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

import audit
import os
import pwd

from opsrest.constants import REST_LOGIN_PATH

aufd = None

class RequiredParameter(Exception): pass

def audit_log_user_msg(op, auditlog_type, uri, cfgdata, user, hostname,
                       addr, result, error_message):
    """
    Simple wrapper function for audit_log_user_message() from the
    audit library to insure a consistent audit event message.

    : param op: Text indicating the configuration operation that was
        performed.  Spaces are not allowed (replace with '-').
        No other special characters should be used.
    : param auditlog_type: Type of event
    : param uri: Request URI
    : param cfgdata: The configuration data that was changed or "None".
    : param user: The name of the user associated with the REST request.
    : param hostname: The hostname of local system, None if unknown.
    : param addr: The network address of the user, None if unknown.
    : param result: Result of the configuration operation.
        1 is "success", 0 is "failed"
    : param error_message: A custom error message for the event
    : return: -1 on failure, otherwise the event number.
    """
    global aufd

    if (aufd == None):
        aufd = audit.audit_open()

    cfg = ""
    if (cfgdata != None):
        cfg = audit.audit_encode_nv_string("data", str(cfgdata), 0)
        if (cfg == None):
            cfg = "out-of-memory!"

    if (op == None):
        raise RequiredParameter("Missing operation text!")

    if (user == None):
        user = pwd.getpwuid(os.getuid()).pw_name

    if uri == REST_LOGIN_PATH and error_message is not None:
        msg = str("op=RESTD:%s uri=%s %s  error_message=%s user=%s"
                  % (op, uri, cfg, error_message, user))
    else:
        msg = str("op=RESTD:%s uri=%s %s  user=%s"
                  % (op, uri, cfg, user))
    res = audit.audit_log_user_message(aufd, auditlog_type,
                                       msg, hostname, addr, None, result)
    return res
