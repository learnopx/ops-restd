# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

# Third party imports
import httplib
import socket
import rbac

from struct import pack, unpack, calcsize
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from tornado.log import app_log
from tornado import gen

# Local imports
from opsrest.exceptions import NotAuthenticated, PasswordChangeError
from opsrest.custom.schemavalidator import SchemaValidator
from opsrest.custom.basecontroller import BaseController
from opsrest.custom.restobject import RestObject
from opsrest.custom.accountvalidator import AccountValidator
from opsrest.custom.passwordserverconfig import PasswordServerConfig
from opsrest.constants import (REQUEST_TYPE_UPDATE, USERNAME_KEY,
                               USER_ROLE_KEY, USER_PERMISSIONS_KEY,
                               OVSDB_SCHEMA_STATUS, PASSWD_MSG_CHG_PASSWORD,
                               PASSWD_USERNAME_SIZE, PASSWD_PASSWORD_SIZE,
                               PASSWD_SRV_GENERIC_ERR, PASSWD_SRV_SOCK_TIMEOUT)

# Password Server Error codes
from opsrest.constants import (PASSWD_ERR_FATAL,
                               PASSWD_ERR_SUCCESS,
                               PASSWD_ERR_USER_NOT_FOUND,
                               PASSWD_ERR_PASSWORD_NOT_MATCH,
                               PASSWD_ERR_INVALID_USER)


class AccountController(BaseController):

    def initialize(self):
        self.schemavalidator = SchemaValidator("account_schema")
        self.validator = AccountValidator()
        self.base_uri_path = "account"
        self.passwd_srv_cfg = PasswordServerConfig()

    def __pad_nul__(self, data, size):
        """
        Receives a string and returns another
        padded with as many NUL characters to
        fill it up to the given size, if its
        length is less than size.
        """
        return "{:\0<{size}}".format(data, size=size)

    def __connect_to_password_server__(self):
        """
        Attempts a connection to the Password Server.
        Returns the socket used to send/receive message
        """

        # Create Unix Domain Socket (UDS)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Set a timeout of PASSWD_SRV_SOCK_TIMEOUT seconds
        # for subsequent blocking socket operations.
        sock.settimeout(PASSWD_SRV_SOCK_TIMEOUT)

        # Attempt connection to the password server
        try:
            app_log.debug("Connecting to Password Server at %s" %
                          self.passwd_srv_cfg.sock_fd)
            sock.connect(self.passwd_srv_cfg.sock_fd)
        except socket.error, msg:
            app_log.debug("Error connecting to Password Server: %s" % msg)
            raise PasswordChangeError(PASSWD_SRV_GENERIC_ERR)

        return sock

    def __format_password_server_message__(self, username, current_password,
                                           new_password):
        """
        Format the message sent to the Password Server.
        The Password Server expects the following struct:
            {opcode, username, oldpasswd, newpasswd}
        Where:
           - opcode is an int
           - username is a char pointer of max size PASSWD_USERNAME_SIZE
           - *passwd: is a char pointer of max size PASSWD_PASSWORD_SIZE
        """

        # Pack opcode as a native int with standardized size
        message = pack('=i', PASSWD_MSG_CHG_PASSWORD)

        # Add all other fields as NUL-padded char pointers
        message += self.__pad_nul__(username, PASSWD_USERNAME_SIZE)
        message += self.__pad_nul__(current_password, PASSWD_PASSWORD_SIZE)
        message += self.__pad_nul__(new_password, PASSWD_PASSWORD_SIZE)

        return message

    def __encrypt_password_server_message__(self, username, current_password,
                                            new_password):
        app_log.info("Encrypting Password Server message using pubkey at %s" %
                     self.passwd_srv_cfg.pub_key_loc)

        # Pack and format the message as expected by the Password Server
        message = self.__format_password_server_message__(username,
                                                          current_password,
                                                          new_password)
        try:
            # Read and import the Password Server's public key
            with open(
             self.passwd_srv_cfg.pub_key_loc, 'r') as pub_key_file:
                pub_key_str = pub_key_file.read()
            pub_key = RSA.importKey(pub_key_str)

            # Encrypt the message with the  server's key
            cipher = PKCS1_OAEP.new(pub_key)
            encrypted_message = cipher.encrypt(message)
        except Exception as e:
            app_log.debug("Failed to encrypt message: %s" % e)
            raise PasswordChangeError(PASSWD_SRV_GENERIC_ERR)

        return encrypted_message

    def __change_user_password__(self, username, current_password,
                                 new_password):
        result = PASSWD_ERR_FATAL

        sock = self.__connect_to_password_server__()

        # Attempt password change
        try:
            message = \
                self.__encrypt_password_server_message__(username,
                                                         current_password,
                                                         new_password)
            # Send message to the Password Server
            if sock.sendall(message) is None:
                app_log.debug("Password server message sent successfully!")

            # Reply is a single native int with standardized size
            fmt = '=i'
            size = calcsize(fmt)

            # Receive Password Server's reply
            # The operation times out after PASSWD_SRV_SOCK_TIMEOUT
            # seconds, this timeout is set during socket creation
            recv_result = sock.recv(size, socket.MSG_WAITALL)
            result = unpack(fmt, recv_result)[0]
            app_log.debug("Password server reply: %s" % result)

        except socket.error, msg:
            app_log.debug("Couldn't send/receive message to password  " +
                          "server: %s" % msg)
            raise PasswordChangeError(PASSWD_SRV_GENERIC_ERR)
        finally:
            sock.close()

        if result != PASSWD_ERR_SUCCESS:
            status_code = httplib.INTERNAL_SERVER_ERROR
            error = "Unable to change password for user '%s'" % username
            if result in (PASSWD_ERR_USER_NOT_FOUND,
                          PASSWD_ERR_PASSWORD_NOT_MATCH,
                          PASSWD_ERR_INVALID_USER):
                status_code = httplib.UNAUTHORIZED
                error = "Invalid credentials for user '%s'" % username

            raise PasswordChangeError(error, status_code)

    def __get_username__(self, current_user):
        if USERNAME_KEY in current_user and \
                current_user[USERNAME_KEY] is not None:
            return current_user[USERNAME_KEY]
        else:
            raise NotAuthenticated("No user currently logged in")

    @gen.coroutine
    def update(self, item_id, data, current_user, query_args):
        """
        Update user from ops_netop group
        Returns result dictionary
        """

        app_log.info("Updating account info...")

        username = self.__get_username__(current_user)

        # Validate json
        self.schemavalidator.validate_json(data, REQUEST_TYPE_UPDATE)

        # Validate user data
        account_info = RestObject.from_json(data)
        self.validator.validate_update(username, account_info)

        # Get user's current and new passwords
        current_password = account_info.configuration.password
        new_password = account_info.configuration.new_password

        # Attempt password change
        self.__change_user_password__(username, current_password, new_password)

    @gen.coroutine
    def get_all(self, current_user, selector=None, query_args=None):
        """
        Get current user's information
        Returns dictionary with user's role and permissions
        """

        app_log.info("Querying account info...")

        username = self.__get_username__(current_user)

        role = rbac.get_user_role(username)
        permissions = rbac.get_user_permissions(username)

        account_info = RestObject.create_empty_json()
        account_info[OVSDB_SCHEMA_STATUS][USER_ROLE_KEY] = role
        account_info[OVSDB_SCHEMA_STATUS][USER_PERMISSIONS_KEY] = permissions

        return account_info
