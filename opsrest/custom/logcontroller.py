#!/usr/bin/python
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
from tornado.log import app_log
from tornado import gen
import subprocess
import json
import re
import time

# Local imports
from opsrest.custom.basecontroller import BaseController
from opsrest.exceptions import DataValidationFailed
from opsrest.constants import *
from opsrest.utils import getutils, jsonutils

# Constants
LOGS_OPTIONS = "options"
LOGS_MATCHES = "matches"
LOGS_PAGINATION = "pagination"
REST_LOGS_PARAM_PRIORITY_OPTION = "priority"
REST_LOGS_PARAM_PRIORITY_MATCH = "PRIORITY"
REST_LOGS_PARAM_SINCE = "since"
REST_LOGS_PARAM_UNTIL = "until"
REST_LOGS_PARAM_AFTER_CURSOR = "after-cursor"
REST_LOGS_PARAM_MESSAGE = "MESSAGE"
REST_LOGS_PARAM_MESSAGE_ID = "MESSAGE_ID"
REST_LOGS_PARAM_PID = "_PID"
REST_LOGS_PARAM_UID = "_UID"
REST_LOGS_PARAM_GID = "_GID"
REST_LOGS_PARAM_SYSLOG_IDENTIFIER = "SYSLOG_IDENTIFIER"
JOURNALCTL_CMD = "journalctl"
OUTPUT_FORMAT = "--output=json"
NEWEST_ENTRY = 0
TRUNCATE_ENTRIES = 1000
MAXLIMIT = 10000
DATETIME_REGEX = '\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d'
MAXPRIORITY = 7
MINPRIORITY = 0


class LogController(BaseController):
    FILTER_KEYWORDS = {LOGS_OPTIONS: [REST_LOGS_PARAM_PRIORITY_OPTION,
                                      REST_LOGS_PARAM_SINCE,
                                      REST_LOGS_PARAM_UNTIL,
                                      REST_LOGS_PARAM_AFTER_CURSOR],
                       LOGS_MATCHES: [REST_LOGS_PARAM_MESSAGE,
                                      REST_LOGS_PARAM_MESSAGE_ID,
                                      REST_LOGS_PARAM_PRIORITY_MATCH,
                                      REST_LOGS_PARAM_PID,
                                      REST_LOGS_PARAM_UID,
                                      REST_LOGS_PARAM_GID,
                                      REST_LOGS_PARAM_SYSLOG_IDENTIFIER],
                       LOGS_PAGINATION: [REST_QUERY_PARAM_OFFSET,
                                         REST_QUERY_PARAM_LIMIT]}

    def initialize(self):
        self.base_uri_path = "logs"

    # This function is to validate the invalid keywords that can be used
    # to use different features of the log api
    def validate_keywords(self, query_args):
        error_fields = []
        if query_args:
            for k, v in query_args.iteritems():
                if not(k in self.FILTER_KEYWORDS[LOGS_PAGINATION] or
                       k in self.FILTER_KEYWORDS[LOGS_OPTIONS] or
                       k in self.FILTER_KEYWORDS[LOGS_MATCHES]):
                    error_fields.append(k)

        if error_fields:
            raise DataValidationFailed("Invalid log filters %s" % error_fields)

    @staticmethod
    def check_offset_param(query_args):
        if REST_QUERY_PARAM_OFFSET in query_args:
            offset = int(getutils.get_query_arg(REST_QUERY_PARAM_OFFSET,
                         query_args))
        else:
            offset = NEWEST_ENTRY

        return offset

    @staticmethod
    def check_limit_param(query_args):
        if REST_QUERY_PARAM_LIMIT in query_args:
            limit = int(getutils.get_query_arg(REST_QUERY_PARAM_LIMIT,
                        query_args))
        else:
            limit = None

        return limit

    # This is a function to cover different validation cases for since and
    # until paramater of logs uri
    @staticmethod
    def validate_since_until(arg, error_messages, time_keywords,
                             time_relative_keywords):
        since_until_arg = arg.split(" ", 1)
        if not(since_until_arg[0] in time_relative_keywords):
            if len(since_until_arg) == 2:
                if not((since_until_arg[1] in time_keywords and
                       (since_until_arg[0].isdigit() and
                        since_until_arg[0] > 0)) or
                       ("0000-00-00 00:00:00" not in arg and
                        re.search(DATETIME_REGEX, arg) is not None)):
                    error_messages.append("Invalid timestamp value used" +
                                          " % s" % arg)
            else:
                error_messages.append("Invalid timestamp value" +
                                      " % s" % since_until_arg[0])

        return error_messages

    @staticmethod
    def validate_priority(priority, error_messages):
        if int(priority) > MAXPRIORITY or int(priority) < MINPRIORITY:
            msg = ("Invalid log level. Priority should be greater than % s and \
                   less than or equal to % s: % s" \
                   % (MINPRIORITY, MAXPRIORITY, priority))
            error_messages.append(msg)

        return error_messages

    # This function is to validate the correctness or range of the data that
    # the user wishes to use for different options or features of the log api
    def validate_args_data(self, query_args):
        error_messages = []
        time_relative_keywords = ["yesterday", "now", "today"]
        time_keywords = ["day ago", "days ago", "minute ago", "minutes ago",
                         "hour ago", "hours ago"]

        offset = getutils.get_query_arg(REST_QUERY_PARAM_OFFSET, query_args)
        if offset is not None:
            if not(offset.isdigit() and int(offset) >= 0):
                error_messages.append("Only positive integers are allowed" +
                                      " for offset")

        limit = getutils.get_query_arg(REST_QUERY_PARAM_LIMIT, query_args)
        if limit is not None:
            if not(limit.isdigit() and int(limit) > 0 and
                   int(limit) <= MAXLIMIT):
                error_messages.append("Valid range for limit is from 1 to" +
                                      "%s" % MAXLIMIT)

        priority = getutils.get_query_arg(REST_LOGS_PARAM_PRIORITY_OPTION,
                                          query_args)
        if priority is not None:
            error_messages = self.validate_priority(priority, error_messages)

        priority_match = getutils.get_query_arg(REST_LOGS_PARAM_PRIORITY_MATCH,
                                                query_args)
        if priority_match is not None:
            error_messages = self.validate_priority(priority_match,
                                                    error_messages)

        since_arg = getutils.get_query_arg(REST_LOGS_PARAM_SINCE, query_args)
        if since_arg is not None:
            error_messages = self.validate_since_until(since_arg,
                                                       error_messages,
                                                       time_keywords,
                                                       time_relative_keywords)

        until_arg = getutils.get_query_arg(REST_LOGS_PARAM_UNTIL, query_args)
        if until_arg is not None:
            error_messages = self.validate_since_until(until_arg,
                                                       error_messages,
                                                       time_keywords,
                                                       time_relative_keywords)

        if error_messages:
            raise DataValidationFailed("Incorrect data for arguments: %s" %
                                       error_messages)

    # This function is used to aggregate the different options from the uri
    # and form a journalctl command to be executed to get the logs
    # desired by the user
    def get_log_cmd_options(self, query_args):
        log_cmd_options = [JOURNALCTL_CMD]

        offset = self.check_offset_param(query_args)
        limit = self.check_limit_param(query_args)

        if limit is None:
            limit_size = TRUNCATE_ENTRIES
        else:
            limit_size = limit

        page_size = str(offset + limit_size)
        log_cmd_options.append("-n" + page_size)

        if query_args:
            for k, v in query_args.iteritems():
                if k not in self.FILTER_KEYWORDS[LOGS_PAGINATION]:
                    if k in self.FILTER_KEYWORDS[LOGS_MATCHES]:
                        log_cmd_options.append(str(k) + "=" + str(v[0]))
                    else:
                        log_cmd_options.append("--" + str(k) + "=" + str(v[0]))

        log_cmd_options.append(OUTPUT_FORMAT)

        return log_cmd_options

    # This function is to handle the after-cursor filter. Since the data for
    # after cursor consists of ';' which is a delimiter for the web queries,
    # this function is required to merge the query arguments for this filter.
    # However when the query is from swagger, ';' is converted to its
    # corresponding ascii, so we have to read after-cursor as it is
    @staticmethod
    def handle_after_cursor(query_args):
        params = ['i', 'b', 'm', 't', 'x']
        if set(params).issubset(set(query_args)):
            for p in params:
                arg = ';' + p + '=' + \
                    str(getutils.get_query_arg(p, query_args))
                del query_args[p]
                query_args[REST_LOGS_PARAM_AFTER_CURSOR][0] += arg
        else:
            tmp = query_args[REST_LOGS_PARAM_AFTER_CURSOR][0]
            query_args[REST_LOGS_PARAM_AFTER_CURSOR][0] = tmp.strip("'")

        return query_args

    @gen.coroutine
    def get_all(self, current_user, selector=None, query_args=None):
        offset = None
        limit = None

        if REST_LOGS_PARAM_AFTER_CURSOR in query_args:
            query_args = self.handle_after_cursor(query_args)

        self.validate_keywords(query_args)
        self.validate_args_data(query_args)
        log_cmd_options = self.get_log_cmd_options(query_args)
        app_log.debug("log command options %s" % log_cmd_options)

        response = {}
        app_log.debug("Calling journalctl")
        try:
            response = subprocess.check_output(log_cmd_options)
        except subprocess.CalledProcessError as c:
            app_log.error("Empty log: %s" % c.output)
            response = {}

        if response:
            response = jsonutils.convert_string_to_json(response)
            app_log.debug("length of response %s" % len(response))
            offset = self.check_offset_param(query_args)
            limit = self.check_limit_param(query_args)
            if offset is not None or limit is not None:
                response = getutils.paginate_get_results(response,
                                                         offset,
                                                         limit)
        else:
            response = {"Empty logs": "No logs present for the combination" +
                        " of arguments selected"}

        return (response)
