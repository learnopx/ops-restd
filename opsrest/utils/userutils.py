# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
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
import pwd
import grp
import rbac
import userauth

from subprocess import PIPE, Popen
from opsrest.exceptions import (
    AuthenticationFailed,
    ForbiddenMethod,
    NotAuthenticated
)
from opsrest.constants import (
    ALLOWED_LOGIN_PERMISSIONS,
    METHOD_PERMISSION_MAP,
    REQUEST_TYPE_OPTIONS
)
from opsrest.settings import settings


def get_group_id(group_name):
    group = grp.getgrnam(group_name)
    return group.gr_gid


def check_user_group(username, group):
    try:
        user_groups = Popen(["groups", username],
                            stdout=PIPE).communicate()[0]
        user_groups = user_groups.rstrip("\n").replace(" :", "").split(" ")

        if group in user_groups:
            return True
        else:
            return False

    except KeyError:
        return False


def user_exists(username):
    try:
        return pwd.getpwnam(username) is not None
    except KeyError:
        return False


def get_user_id(username):
    try:
        return pwd.getpwnam(username).pw_uid
    except KeyError:
        return None


def get_group_members(group_name):
    all_users = pwd.getpwall()
    all_users_group = []
    group_id = get_group_id(group_name)
    for user in all_users:
        if user.pw_gid == group_id:
            all_users_group.append(user)
    return all_users_group


def get_group_user_count(group_name):
    return len(get_group_members(group_name))


def check_user_login_authorization(username):
    if username and user_exists(username):
        permissions = set(rbac.get_user_permissions(username))
        if not permissions:
            raise AuthenticationFailed('user has no associated permissions')
        # isdisjoint is True if user's permissions and
        # allowed permissions intersection is empty
        if permissions.isdisjoint(ALLOWED_LOGIN_PERMISSIONS):
            raise AuthenticationFailed('user permissions not authorized')
    else:
        raise AuthenticationFailed('username does not exist')


def check_authenticated(req_handler, req_method):
    if settings['auth_enabled'] and req_method != REQUEST_TYPE_OPTIONS:
        is_authenticated = userauth.is_user_authenticated(req_handler)
    else:
        is_authenticated = True

    if not is_authenticated:
        raise NotAuthenticated


def check_method_permission(req_handler, method):
    # Check permissions only if authentication is enabled
    # Plus, OPTIONS is allowed for unauthenticated users
    if method != REQUEST_TYPE_OPTIONS:
        username = req_handler.get_current_user()
        if username is None:
            if settings['auth_enabled']:
                raise NotAuthenticated
        else:
            permissions = rbac.get_user_permissions(username)
            if METHOD_PERMISSION_MAP[method] not in permissions:
                raise ForbiddenMethod
