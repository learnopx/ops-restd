# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
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

from opsrest.constants import *
from opsrest.utils import utils
from opsrest.verify import convert_string_to_value_by_type
from opsrest.exceptions import DataValidationFailed

import re


def get_depth_param(query_arguments):

    depth = 0

    depth_param = get_query_arg(REST_QUERY_PARAM_DEPTH, query_arguments)
    if depth_param:
        try:
            depth = int(depth_param)
            if depth < DEPTH_MIN_VALUE or depth > DEPTH_MAX_VALUE:
                error_json = utils.to_json_error("Depth parameter must be " +
                                                 "greater or equal than " +
                                                 str(DEPTH_MIN_VALUE) + " " +
                                                 "and lower or equal than " +
                                                 str(DEPTH_MAX_VALUE))
                return {ERROR: error_json}

        except ValueError:
            error_json = utils.to_json_error("Depth parameter must " +
                                             "be a number")
            return {ERROR: error_json}

    return depth


def get_query_arg(name, query_arguments):
    arg = None
    if query_arguments is not None and name in query_arguments:
        arg = query_arguments[name][0]
    return arg


def get_param_list(query_arguments, query_param_name):
    arguments = []
    if query_arguments is not None and \
            query_param_name in query_arguments:
        arguments = query_arguments[query_param_name]

    values = []

    for arg in arguments:
        split_args = arg.split(",")
        values.extend(split_args)

    return values


def get_valid_key_values(key_values, schema, resource):
    # Validate schema keys
    valid_key_values = []
    valid_keys = _get_valid_keys(schema, resource)

    for value in key_values:
        if value in valid_keys:
            valid_key_values.append(value)
        else:
            raise DataValidationFailed("Invalid key: %s" % value)

    return valid_key_values


def validate_query_args(sorting_args, filter_args, pagination_args,
                        keys_args, query_arguments, schema, resource=None,
                        depth=0, is_collection=True):

    # Non-plural resources only required to validate if
    # sort, filter, or pagination parameters are NOT present
    if not is_collection:
        return validate_non_plural_query_args(query_arguments)

    # For collection resources, go ahead and
    # validate correctness of all parameters
    staging_sort_data = get_sorting_args(query_arguments, schema,
                                         resource)

    # get_sorting_args returns a list of column
    # names to sort by or an ERROR dictionary
    if ERROR in staging_sort_data:
        return staging_sort_data
    else:
        sorting_args.extend(staging_sort_data)

    # specific column retrieval
    staging_keys_data = get_keys_args(query_arguments, schema,
                                      resource)

    # get_keys_args returns a list of column
    # names to show or an ERROR dictionary
    if ERROR in staging_keys_data:
        return staging_keys_data
    else:
        keys_args.extend(staging_keys_data)

    # get_filters_args returns a dictionary with
    # either filter->value pairs or an ERROR
    filter_args.update(get_filters_args(query_arguments, schema,
                                        resource))

    if ERROR in filter_args:
        return filter_args

    offset = None
    limit = None

    try:
        limit = get_query_arg(REST_QUERY_PARAM_LIMIT, query_arguments)
        offset = get_query_arg(REST_QUERY_PARAM_OFFSET, query_arguments)

        if offset is not None:
            offset = int(offset)

        if limit is not None:
            limit = int(limit)

        pagination_args[REST_QUERY_PARAM_OFFSET] = offset
        pagination_args[REST_QUERY_PARAM_LIMIT] = limit

    except:
        error_json = utils.to_json_error("Pagination indexes must be numbers")
        return {ERROR: error_json}

    if depth == 0 and (sorting_args or filter_args or keys_args or
                       offset is not None or limit is not None):
        error_json = utils.to_json_error("Sort, filter, keys and " +
                                         "pagination parameters are only " +
                                         "supported for depth > 0")
        return {ERROR: error_json}

    return {}


def validate_non_plural_query_args(query_arguments):

    error_json = utils.to_json_error("Sort, filter, pagination and keys " +
                                     "parameters are only supported " +
                                     "for resource collections")
    error_json = {ERROR: error_json}

    # Check if sort or pagination parameters are present

    # NOTE any new query keys should be added to this condition
    if REST_QUERY_PARAM_SORTING in query_arguments or \
            REST_QUERY_PARAM_OFFSET in query_arguments or \
            REST_QUERY_PARAM_LIMIT in query_arguments or \
            REST_QUERY_PARAM_KEYS in query_arguments:
        return error_json

    # To detect if filter arguments (valid or not) are present,
    # remove anything else valid, and check if something was left.
    # At this point sort and pagination parameters should not be
    # present as they are validated above

    # NOTE any new query key valid for non-plural
    # resources should be added here

    valid_keys_count = 0
    if REST_QUERY_PARAM_SELECTOR in query_arguments:
        valid_keys_count += 1

    if REST_QUERY_PARAM_DEPTH in query_arguments:
        valid_keys_count += 1

    invalid_keys_count = len(query_arguments) - valid_keys_count

    if invalid_keys_count > 0:
        return error_json
    else:
        return {}


def get_keys_args(query_arguments, schema, resource=None):
    keys_values = get_param_list(query_arguments, REST_QUERY_PARAM_KEYS)

    valid_keys_values = []

    if keys_values:
        valid_keys_values = get_valid_key_values(keys_values, schema,
                                                 resource)

    return valid_keys_values


def get_sorting_args(query_arguments, schema, resource=None):
    sorting_values = get_param_list(query_arguments, REST_QUERY_PARAM_SORTING)

    valid_sorting_values = []

    if sorting_values:

        regexp = re.compile('^([\-]?)(.*)$')

        match_order = regexp.match(sorting_values[0])

        # The parameter might include a - (indicating descending order)
        # prepended to the column name, default sorting is ascending
        # and this is represented as False in the reverse parameter
        # of sorted(), so here it's appended to the end of the
        # sorting arguments

        if match_order:
            order, value = match_order.groups()
            if order == '-':
                order = True
            else:
                order = False
            sorting_values[0] = value

            valid_sorting_values = get_valid_key_values(sorting_values, schema,
                                                        resource)

            if valid_sorting_values:
                valid_sorting_values.append(order)

    return valid_sorting_values


def _get_valid_keys(schema, resource=None):
    valid_keys = []

    # Get valid keys for the ovsdb schema
    if hasattr(schema, "ovs_tables"):

        valid_keys.extend(resource.keys[OVSDB_SCHEMA_CONFIG].keys())

        valid_keys.extend(resource.keys[OVSDB_SCHEMA_STATUS].keys())

        valid_keys.extend(resource.keys[OVSDB_SCHEMA_STATS].keys())

        references = resource.keys[OVSDB_SCHEMA_REFERENCE]
        references_keys = references.keys()

        valid_keys.extend(references_keys)

    # Get valid keys from standard JSON schema
    else:
        p = 'properties'
        for category in VALID_CATEGORIES:
            if category in schema[p] and p in schema[p][category]:
                valid_keys.extend(schema[p][category][p].keys())

    return valid_keys


def get_filters_args(query_arguments, schema, resource=None):
    filters = {}
    if query_arguments is not None:
        valid_keys = _get_valid_keys(schema, resource)

        for key in query_arguments:
            # NOTE any new query keys should be added to this condition
            if key in (REST_QUERY_PARAM_LIMIT, REST_QUERY_PARAM_OFFSET,
                       REST_QUERY_PARAM_DEPTH, REST_QUERY_PARAM_SORTING,
                       REST_QUERY_PARAM_SELECTOR, REST_QUERY_PARAM_KEYS):
                continue
            elif key in valid_keys:
                filters[key] = []
                for filter_ in query_arguments[key]:
                    filters[key].extend(filter_.split(","))
            else:
                error_json = \
                    utils.to_json_error("Invalid filter column: %s" % key)
                return {ERROR: error_json}

    return filters


def post_process_get_data(get_data, sorting_args, filter_args, offset, limit,
                          keys_args, schema, table=None,
                          categorized=False):

    processed_get_data = get_data

    # TODO this should be moved to where each row is processed

    # Filter results if necessary
    if filter_args:
        processed_get_data = \
            filter_get_results(processed_get_data, filter_args,
                               schema, table, categorized)

    # Sort results if necessary
    if sorting_args:
        # Last sorting argument is a boolean
        # indicating if sort should be reversed
        reverse_sort = sorting_args.pop()
        processed_get_data = sort_get_results(processed_get_data,
                                              sorting_args,
                                              reverse_sort,
                                              categorized)

    # Specific keys retrieval results if necessary
    if keys_args:
        processed_get_data = remove_unwanted_keys(processed_get_data,
                                                  keys_args,
                                                  categorized)

    # Paginate results if necessary
    processed_get_data = paginate_get_results(processed_get_data,
                                              offset, limit)

    return processed_get_data


def filter_get_results(get_data, filters, schema, table=None,
                       categorized=False):
    filtered_data = []
    for element in get_data:
        valid = True
        for key in filters:
            value = None
            if categorized:
                for category in VALID_CATEGORIES:
                    if category in element \
                       and key in element[category]:
                        value = element[category][key]
                        break
            else:
                if key in element:
                    value = element[key]
            if value:
                column_type = _get_column_type(key, schema, table)
                filter_set = _process_filters(filters[key], column_type)

                if type(value) is list:
                    value_set = set(value)
                else:
                    value_set = set([value])

                if filter_set.difference(value_set) == filter_set:
                    valid = False
            else:
                valid = False

        if valid:
            filtered_data.append(element)

    return filtered_data


def _get_column_type(column, schema, table=None):

    column_type = None

    # Process column from ovsdb schema
    if hasattr(schema, "ovs_tables"):
        if column in schema.ovs_tables[table].config:
            column_type = schema.ovs_tables[table].config[column].type
        elif column in schema.ovs_tables[table].status:
            column_type = schema.ovs_tables[table].status[column].type
        elif column in schema.ovs_tables[table].stats:
            column_type = schema.ovs_tables[table].stats[column].type
        elif column in schema.ovs_tables[table].references:
            column_type = schema.ovs_tables[table].references[column].type

    # Process column from standard JSON schema
    else:
        p = 'properties'
        simple_types = {
            'array': list,
            'boolean': bool,
            'integer': int,
            'null': None,
            'number': float,
            'object': dict,
            'string': str
        }
        for category in (OVSDB_SCHEMA_CONFIG, OVSDB_SCHEMA_STATS,
                         OVSDB_SCHEMA_STATUS):
            if category in schema[p] and p in schema[p][category] and \
                    column in schema[p][category][p]:
                _type = schema[p][category][p][column]['type']
                if _type in simple_types:
                    column_type = simple_types[_type]

    return column_type


def _process_filters(filters, column_type):

    filter_set = set([])

    if type(filters) is list:
        filter_list = filters
    else:
        filter_list = [filters]

    for f in filter_list:
        value = convert_string_to_value_by_type(f, column_type)
        if value is not None:
            filter_set.add(value)

    return filter_set


def process_sort_value(item, key, categorized):
    value = None
    if categorized:
        for category in VALID_CATEGORIES:
            if category in item and key in item[category]:
                value = item[category][key]
                break
    else:
        if key in item:
            value = item[key]
    if value is not None:
        if isinstance(value, str):
            value = value.lower()
    else:
        # We might in the future need to change this to
        # process the value's type accordingly, but sort
        # is currently done ascii-wise so this should be ok.
        value = ""
    return value


def sort_get_results(get_data, sort_by_columns, reverse_=False,
                     categorized=False):

    # The lambda function returns a tuple with the comparable
    # values of each column, so that sorted() use them as the
    # compare keys for dictionaries in the GET results
    sorted_data = sorted(
        get_data,
        key=lambda item: tuple(process_sort_value(item, k,
                                                  categorized)
                               for k in sort_by_columns),
        reverse=reverse_)

    return sorted_data


def remove_unwanted_keys(get_data, retrieve_by_keys, categorized=False):
    for row in get_data:
        row_keys = []
        if categorized:
            for category in VALID_CATEGORIES:
                if category in row:
                    row_keys.extend(row[category].keys())
        else:
            row_keys = row.keys()
        keys_to_remove = list(set(row_keys) - set(retrieve_by_keys))
        for key in keys_to_remove:
            if categorized:
                for category in VALID_CATEGORIES:
                    if category in row and key in row[category]:
                        row[category].pop(key)
            else:
                row.pop(key)
    return get_data


def paginate_get_results(get_data, offset=None, limit=None):

    data_length = len(get_data)

    if offset is None:
        if limit is None:
            return get_data
        else:
            offset = 0

    # limit is exclusive
    if limit is None:
        limit = data_length
    else:
        limit = offset + limit

    error_json = {}
    if offset < 0 or offset > data_length:
        error_json = utils.to_json_error("Pagination index out of range",
                                         None, REST_QUERY_PARAM_OFFSET)

    elif limit < 0:
        error_json = utils.to_json_error("Pagination index out of range",
                                         None, REST_QUERY_PARAM_LIMIT)

    elif offset >= limit:
        error_json = utils.to_json_error("Pagination offset can't be equal " +
                                         "or greater than offset + limit")

    if error_json:
        return {ERROR: error_json}

    sliced_get_data = get_data[offset:limit]

    return sliced_get_data


def _categorize_by_selector(config_data, stats_data, status_data, selector):

    data = {}
    if selector == OVSDB_SCHEMA_CONFIG:
        data = {OVSDB_SCHEMA_CONFIG: config_data}
    elif selector == OVSDB_SCHEMA_STATS:
        data = {OVSDB_SCHEMA_STATS: stats_data}
    elif selector == OVSDB_SCHEMA_STATUS:
        data = {OVSDB_SCHEMA_STATUS: status_data}
    else:
        data = {OVSDB_SCHEMA_CONFIG: config_data, OVSDB_SCHEMA_STATS:
                stats_data, OVSDB_SCHEMA_STATUS: status_data}

    return data


def is_empty_value(value):
    return value is None or value == {} or value == []
