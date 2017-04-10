#!/usr/bin/env python
# Copyright (C) 2015-2016 Hewlett-Packard Enterprise Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import getopt
import re
import string
import sys

import inflect

from copy import deepcopy
import ovs.daemon
from ovs.db import error, types
import ovs.db.idl
import ovs.dirs
import ovs.util


# Global variables
inflect_engine = inflect.engine()

# Schema constants
OVSDB_SCHEMA_CONFIG = 'configuration'
OVSDB_SCHEMA_STATS = 'statistics'
OVSDB_SCHEMA_STATUS = 'status'
OVSDB_SCHEMA_REFERENCE = 'reference'
OVSDB_CATEGORY_PERVALUE = 'per-value'
OVSDB_CATEGORY_FOLLOWS = 'follows'

# Relationship type map
RELATIONSHIP_MAP = {
    '1:m': 'child',
    'm:1': 'parent',
    'reference': 'reference'
}

# On demand fetched tables
FETCH_TYPE_PARTIAL = 0
FETCH_TYPE_FULL = 1
ON_DEMAND_FETCHED_TABLES = {
    "BGP_Route": FETCH_TYPE_PARTIAL,
    "BGP_Nexthop": FETCH_TYPE_PARTIAL,
    "Route": FETCH_TYPE_PARTIAL,
    "Nexthop": FETCH_TYPE_PARTIAL
}


# Convert name into all lower case and into plural (default) or singular format
def normalizeName(name, to_plural=True):
    lower_case = name.lower()
    # Assuming table names use underscore to link words
    words = string.split(lower_case, '_')

    if to_plural:
        words[-1] = inflect_engine.plural_noun(words[-1])
    else:
        words[-1] = inflect_engine.singular_noun(words[-1])

    return(string.join(words, '_'))


class OVSColumn(object):
    '''
    An instance of OVSColumn represents a column
    from the OpenSwitch Extended Schema. Attributes:

    - name: the column's name
    - category: the column's category
    - is_optional: whether the column is required to have a value
    - mutable: whether the column is modifiable after creation
    - enum: possible values for the column or column's keys
    - type: the column's (or key's) base type
    - rangeMin: the column's (or key's) data range
    - rangeMax: the column's (or key's) data range
    - value_type: if a map, the value's base type
    - valueRangeMin: if a map, the value's data range
    - valueRangeMax: if a map, the value's data range
    - is_dict: whether the column is a map/dictionary
    - is_list: whether the column is a list
    - n_min: the column's minimum number of elements
    - n_max: the column's maximum number of elements
    - kvs: if a map, this holds each key's value type information
    - keyname: name used to identify the reference (if a kv reference)
    - desc: the column's documentation/description text
    - emptyValue: value assumed for the column, if is_optional=True and empty
    '''
    def __init__(self, table_name, column_name, ovs_base_type,
                 is_optional=True, mutable=True, category=None,
                 emptyValue=None, valueMap=None, keyname=None,
                 col_doc=None, group=None, loadDescription=False):

        key_type = ovs_base_type.key
        value_type = ovs_base_type.value

        self.name = column_name
        self.category = category
        self.is_optional = is_optional
        self.emptyValue = emptyValue
        self.mutable = mutable
        self.enum = key_type.enum
        self.keyname = keyname

        # Process the column's (or key's) base type
        self.type, self.rangeMin, self.rangeMax = self.process_type(key_type)

        # If a map, process the value's base type
        self.value_type = None
        if value_type is not None:
            self.value_type, self.valueRangeMin, self.valueRangeMax = \
                self.process_type(value_type)

        # Information regarding the column's nature and number of elements
        self.is_dict = self.value_type is not None
        self.is_list = (not self.is_dict) and ovs_base_type.n_max > 1
        self.n_max = ovs_base_type.n_max
        self.n_min = ovs_base_type.n_min

        self.kvs = {}
        self.process_valuemap(valueMap, loadDescription)
        self.desc = col_doc

    def process_valuemap(self, valueMap, loadDescription):
        '''
        Processes information from the valueMap data structure in the
        extended schema and fills the kvs dictionary for this column
        '''

        for key, value in valueMap.iteritems():

            self.kvs[key] = {}

            # Process the values's type
            base_type = types.BaseType.from_json(value['type'])
            _type, _min, _max = self.process_type(base_type)
            enum = base_type.enum

            # Store this key's type information in kvs
            self.kvs[key]['type'] = _type
            self.kvs[key]['rangeMin'] = _min
            self.kvs[key]['rangeMax'] = _max
            self.kvs[key]['enum'] = enum

            # Setting is_optional per key so that eventually
            # it can be set per key from data in the schema,
            # REST's validation should already check this.
            self.kvs[key]['is_optional'] = self.is_optional

            # Process this key's documentation information
            self.kvs[key]['desc'] = None
            self.kvs[key]['group'] = None

            if loadDescription:
                if 'doc' in value:
                    self.kvs[key]['desc'] = ' '.join(value['doc'])
                if 'group' in value:
                    self.kvs[key]['group'] = value['group']

    def process_type(self, base):
        __type = base.type
        rangeMin = None
        rangeMax = None

        if __type == types.StringType:

            if base.min_length is None:
                rangeMin = 0
            else:
                rangeMin = base.min_length

            if base.max_length is None:
                rangeMax = sys.maxint
            else:
                rangeMax = base.max_length

        elif __type == types.UuidType:
            rangeMin = None
            rangeMax = None

        elif __type != types.BooleanType:

            if base.min is None:
                rangeMin = 0
            else:
                rangeMin = base.min

            if base.max is None:
                rangeMax = sys.maxint
            else:
                rangeMax = base.max

        return (__type, rangeMin, rangeMax)


class OVSReference(OVSColumn):
    '''
    An instance of OVSReference represents a column from the OpenSwitch
    Extended Schema that contains references to other tables. Attributes not
    inherited from OVSColumn:

    - kv_type: whether this is a kv reference
    - kv_key_type: if a kv reference, the type of the key
    - ref_table: the table to reference
    - relation: relationship type between this column and the referenced table
    - is_plural: whether the column is plural
    '''
    def __init__(self, table_name, column_name, ovs_base_type,
                 is_optional=True, mutable=True, category=None, valueMap=None,
                 keyname=None, col_doc=None, group=None,
                 relation=OVSDB_SCHEMA_REFERENCE, loadDescription=False):

        super(OVSReference, self).__init__(table_name, column_name,
                                           ovs_base_type, is_optional, mutable,
                                           category, None, valueMap, keyname,
                                           col_doc, group, loadDescription)

        key_type = ovs_base_type.key

        # Information of the table being referenced
        self.kv_type = False
        if key_type.type != types.UuidType:
            # referenced table name must be in value part of KV pair
            self.kv_type = True
            self.kv_key_type = key_type.type
            key_type = ovs_base_type.value
        self.ref_table = key_type.ref_table_name

        # Overwrite parsed type from parent class processing
        self.type = key_type

        # Relationship of the referenced to the current table
        # one of child, parent or reference
        if relation not in RELATIONSHIP_MAP.values():
            raise error.Error('unknown table relationship %s' % relation)
        else:
            self.relation = relation

        # The number of instances
        self.is_plural = (self.n_max != 1)


class OVSColumnCategory(object):
    def __init__(self, category):
        self.dynamic = False
        self.value = None
        self.validate(category)

        # Process category type
        if isinstance(category, dict):
            per_value_list = category.get(OVSDB_CATEGORY_PERVALUE,
                                          None)
            self.per_value = {}

            if per_value_list:
                for value_dict in per_value_list:
                    self.check_category(value_dict['category'])
                    self.per_value[value_dict['value']] = \
                        value_dict['category']

            self.follows = category.get(OVSDB_CATEGORY_FOLLOWS,
                                        None)
            self.value = OVSDB_SCHEMA_CONFIG
            self.dynamic = True

        elif isinstance(category, (str, unicode)):
            self.value = category

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        elif isinstance(other, (str, unicode)):
            return self.value == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def validate(self, category):
        if category:
            if isinstance(category, dict):
                if not (OVSDB_CATEGORY_PERVALUE in category or
                        OVSDB_CATEGORY_FOLLOWS in category):
                    raise error.Error('Unknown category object '
                                      'attributes')

            elif isinstance(category, (str, unicode)):
                self.check_category(category)
            else:
                raise error.Error('Unknown category type %s' % type(category))

    def check_category(self, category):
        if category not in [OVSDB_SCHEMA_CONFIG,
                            OVSDB_SCHEMA_STATS,
                            OVSDB_SCHEMA_STATUS]:
            raise error.Error('Unknown category: %s' % value)


class OVSTable(object):
    '''__init__() functions as the class constructor'''
    def __init__(self, name, is_root, is_many=True, desc=None,
                 groupsDesc=None):
        self.name = name
        self.plural_name = normalizeName(name)

        self.is_root = is_root

        # List of all column names
        self.columns = []

        # List of read-only column names
        self.readonly_columns = []

        # Is the table in plural form?
        self.is_many = is_many

        # Dictionary of configuration attributes (RW)
        # column name to OVSColumn object mapping
        self.config = {}

        # Copy of configuration attributes
        self.default_config = {}

        # Dictionary of status attributes (Read-only)
        # column name to OVSColumn object mapping
        self.status = {}

        # Dictionary of statistics attributes (Read-only)
        # column name to OVSColumn object mapping
        self.stats = {}

        # Dictionay with category that is an object type
        self.dynamic = {}

        # Parent table name
        self.parent = None

        # Child table list
        self.children = []

        # List of table referenced
        # table name to OVSReference object mapping
        self.references = {}

        # TODO: index columns are those columns that
        # OVSDB uses for indexing rows in a table.
        self.index_columns = None

        # TODO: indexes was introduced to create unique URIs for
        # resources. This is not always equal to index_columns
        # and is a source of confusion. This should be removed
        # eventually.
        self.indexes = None

        # Table's documentation strings. Named 'desc' to keep
        # consistency with the 'desc' attribute in OVSColumn
        self.desc = desc

        # Table's documentation strings for group descriptions
        self.groupsDesc = groupsDesc

    @staticmethod
    def from_json(_json, name, loadDescription):
        parser = ovs.db.parser.Parser(_json, 'schema of table %s' % name)
        columns_json = parser.get('columns', [dict])
        mutable = parser.get_optional('mutable', [bool], True)
        is_root = parser.get_optional('isRoot', [bool], False)
        max_rows = parser.get_optional('maxRows', [int])
        indexes_json = parser.get_optional('indexes', [list], [[]])

        doc = None
        groupsDoc = None

        # Though these will not be used if documentation is not
        # loaded, they have to be parsed or OVS' Parser will fail
        _title = parser.get_optional('title', [str, unicode])
        _doc = parser.get_optional('doc', [list, str, unicode])
        _groups_doc = parser.get_optional('groupDoc', [dict])

        if loadDescription:
            doc = []
            if _title:
                doc = [_title]
            if _doc:
                doc.extend(_doc)
            doc = ' '.join(doc)

            if _groups_doc:
                groupsDoc = _groups_doc

        parser.finish()

        if max_rows is None:
            max_rows = sys.maxint
        elif max_rows <= 0:
            raise error.Error('maxRows must be at least 1', _json)

        if not columns_json:
            raise error.Error('table must have at least one column', _json)

        table = OVSTable(name, is_root, max_rows != 1, desc=doc,
                         groupsDesc=groupsDoc)
        table.index_columns = indexes_json[0]

        for column_name, column_json in columns_json.iteritems():
            parser = ovs.db.parser.Parser(column_json, 'column %s' % name)
            # The category can be a str or a object. The object inside can
            # have the following keys:
            # per-value: matches the possible value with the desired category
            # follows: Reference to the column used to determine the column
            #          category
            category = OVSColumnCategory(parser.get_optional('category',
                                                             [str, unicode,
                                                              dict]))
            relationship = parser.get_optional('relationship', [str, unicode])
            mutable = parser.get_optional('mutable', [bool], True)

            # Ephemereal is not used (yet) in REST, but it's
            # parsed so that the parser does not give an error
            parser.get_optional('ephemeral', [bool], False)

            emptyValue = parser.get_optional('emptyValue',
                                             [int, str, unicode, bool])
            keyname = parser.get_optional('keyname', [str, unicode])

            # Pre-process type, cleaning it up from OPS modifications
            # (e.g. 'valueMap', valueType, adding back 'set' to the
            # enum format)
            _type = parser.get('type', [dict, str, unicode])
            convert_enums(_type)
            valueMap = {}
            if isinstance(_type, dict):
                _type.pop('omitCodeGeneration', None)
                valueMap = _type.pop('valueMap', {})
                if valueMap:
                    _type['key'] = 'string'
                    _type['value'] = _type.pop('valueType', 'string')

            # Load OVS type from type dictionary
            _type = types.Type.from_json(_type)

            # Parse global description for the column

            col_doc = None
            group = None

            # Though these will not be used if documentation is not
            # loaded, they have to be parsed or OVS' Parser will fail
            _col_doc = parser.get_optional('doc', [list])
            _group = parser.get_optional('group', [list, str, unicode])

            if loadDescription:
                if _col_doc:
                    col_doc = ' '.join(_col_doc)
                group = _group

            parser.finish()

            is_column_skipped = False
            is_readonly_column = False
            is_optional = False
            if isinstance(column_json['type'], dict):
                if ('min' in column_json['type'] and
                        column_json['type']['min'] == 0):
                    is_optional = True

            # An attribute will be able to get marked with relationship
            # and category tags simultaneously. We are utilizing the
            # new form of tagging as a second step.
            # For now, we are using only one tag.

            _mutable = mutable
            if relationship is not None:

                # A non-configuration OVSDB_SCHEMA_REFERENCE is never mutable,
                # otherwise the parsed mutable flag is used
                if relationship == OVSDB_SCHEMA_REFERENCE and \
                        category != OVSDB_SCHEMA_CONFIG:
                    _mutable = False

                _relationship = RELATIONSHIP_MAP[relationship]

                table.references[column_name] = OVSReference(table.name,
                                                             column_name,
                                                             _type,
                                                             is_optional,
                                                             _mutable,
                                                             category,
                                                             valueMap,
                                                             keyname,
                                                             col_doc,
                                                             group,
                                                             _relationship,
                                                             loadDescription)

            else:

                # Status and statistics columns are always mutable
                if category != OVSDB_SCHEMA_CONFIG:
                    _mutable = True

                ovs_column = OVSColumn(table.name, column_name, _type,
                                       is_optional, _mutable, category,
                                       emptyValue, valueMap, keyname,
                                       col_doc, group, loadDescription)

                # Save the column in its category group
                if category == OVSDB_SCHEMA_CONFIG:
                    if name in ON_DEMAND_FETCHED_TABLES and \
                        ON_DEMAND_FETCHED_TABLES[name] == FETCH_TYPE_FULL:
                         is_readonly_column = True

                    table.config[column_name] = ovs_column

                elif category == OVSDB_SCHEMA_STATUS:
                    is_readonly_column = True
                    table.status[column_name] = ovs_column

                elif category == OVSDB_SCHEMA_STATS:
                    is_readonly_column = True
                    table.stats[column_name] = ovs_column

                else:
                    # Skip columns that do not have a handled relationship or
                    # category.
                    is_column_skipped = True

            # Add to the array the name of the dynamic column
            if category.dynamic:
                table.dynamic[column_name] = category

            # If the column is readonly, check if it is an index. Indexes
            # should not be registered as readonly columns in the case of a
            # partial fetching. In full fetch, no columns are subscribed to, so
            # consider all columns as readonly columns
            if name in ON_DEMAND_FETCHED_TABLES and is_readonly_column:
                if ON_DEMAND_FETCHED_TABLES[name] == FETCH_TYPE_PARTIAL and \
                     column_name in table.index_columns:
                    pass
                else:
                    table.readonly_columns.append(str(column_name))

            if not is_column_skipped:
                table.columns.append(str(column_name))

        # deepcopy of config attributes to prevent modification
        # of config attributes when updating dynamic categories
        table.default_config = deepcopy(table.config)

        # Validate dynamic categories consistency
        for column_name, category in table.dynamic.iteritems():
            if category.follows is not None\
               and category.follows not in table.columns:
                raise error.Error('Follows column "%s"'
                                  'doesn\'t exists at table "%s"'
                                  % (category.follows, name))

        # TODO: indexes should be removed eventually
        table.indexes = []
        if not table.index_columns:
            table.indexes = ['uuid']
        else:
            for item in table.index_columns:
                if item in table.references and\
                        table.references[item].relation == 'parent':
                    continue
                table.indexes.append(item)

        return table


class RESTSchema(object):
    '''Schema for REST interface from an OVSDB database.'''

    def __init__(self, name, version, tables, doc=None):
        self.name = name
        self.version = version
        self.doc = doc
        # A dictionary of table name to OVSTable object mappings
        self.ovs_tables = tables

        # get a table name map for all references
        self.reference_map = {}
        for table in self.ovs_tables:
            for k, v in self.ovs_tables[table].references.iteritems():
                if k not in self.reference_map:
                    self.reference_map[k] = v.ref_table

        # tables that has the references to one table
        self.references_table_map = {}
        for table in self.ovs_tables:
            tables_references = get_references_tables(self, table)
            self.references_table_map[table] = tables_references

        # get a plural name map for all tables
        self.plural_name_map = {}
        for table in self.ovs_tables.itervalues():
            self.plural_name_map[table.plural_name] = table.name

    @staticmethod
    def from_json(_json, loadDescription):
        parser = ovs.db.parser.Parser(_json, 'extended OVSDB schema')

        # These are not used (yet), but the parser fails if they are not parsed
        parser.get_optional('$schema', [str, unicode])
        parser.get_optional('id', [str, unicode])

        name = parser.get('name', ['id'])
        version = parser.get_optional('version', [str, unicode])
        tablesJson = parser.get('tables', [dict])

        doc = None
        # Though these will not be used if documentation is not
        # loaded, they have to be parsed or OVS' Parser will fail
        _doc = parser.get_optional('doc', [list])

        if loadDescription:
            if _doc:
                doc = ' '.join(_doc)

        parser.finish()

        if (version is not None and
                not re.match('[0-9]+\.[0-9]+\.[0-9]+$', version)):
                raise error.Error('schema version "%s" not in format x.y.z'
                                  % version)

        tables = {}
        for tableName, tableJson in tablesJson.iteritems():
            tables[tableName] = OVSTable.from_json(tableJson, tableName,
                loadDescription)

        # Backfill the parent/child relationship info, mostly for
        # parent pointers which cannot be handled in place.
        for tableName, table in tables.iteritems():
            for columnName, column in table.references.iteritems():
                if column.relation == 'child':
                    table.children.append(columnName)
                    if tables[column.ref_table].parent is None:
                        tables[column.ref_table].parent = tableName
                elif column.relation == 'parent':
                    if tableName not in tables[column.ref_table].children:
                        tables[column.ref_table].children.append(tableName)
                    table.parent = column.ref_table

        return RESTSchema(name, version, tables, doc)


def convert_enums(_type):
    '''
    Looks for enums recursively in the dictionary and
    converts them from a list of keywords, to an OVS 'set'.
    E.g. from 'enum': [<keywords>] to 'enum': ['set', [<keywords>]]
    '''

    if isinstance(_type, dict):
        if 'enum' in _type:
            _type['enum'] = ['set', _type['enum']]
        else:
            for key in _type:
                if isinstance(_type[key], dict):
                    convert_enums(_type[key])


def get_references_tables(schema, ref_table):
    table_references = {}
    for table in schema.ovs_tables:
        columns = []
        references = schema.ovs_tables[table].references
        for column_name, reference in references.iteritems():
            if reference.ref_table == ref_table:
                columns.append(column_name)
        if columns:
            table_references[table] = columns
    return table_references


def is_immutable(table, schema):

    '''
    A table is considered IMMUTABLE if REST API cannot add or
    delete a row from it
    '''
    table_schema = schema.ovs_tables[table]

    # ROOT table
    if table_schema.is_root:
        # CASE 1: if there are no indices, a root table is considered
        #         IMMUTABLE for REST API
        # CASE 2: if there is at least one index of category
        #         OVSDB_SCHEMA_CONFIG, a root table is considered
        #         MUTABLE for REST API

        # NOTE: an immutable table can still be modified by other daemons
        # running on  the switch. For example, system daemon can modify
        # FAN table although REST cannot
        return not _has_config_index(table, schema)

    else:

        # top level table e.g. Port
        if table_schema.parent is None:
            return not _has_config_index(table, schema)
        else:
            # child e.g. Bridge
            # check if the reference in 'parent'
            # is of category OVSDB_SCHEMA_CONFIG
            parent = table_schema.parent
            parent_schema = schema.ovs_tables[parent]
            children = parent_schema.children

            regular_children = []
            for item in children:
                if item in parent_schema.references:
                    regular_children.append(item)

            ref = None
            if table not in parent_schema.children:
                for item in regular_children:
                    if parent_schema.references[item].ref_table == table:
                        ref = item
                        break

                if parent_schema.references[ref].category == \
                        OVSDB_SCHEMA_CONFIG:
                    return False

            else:
                # back children
                return not _has_config_index(table, schema)

    return True


def _has_config_index(table, schema):
    '''
    return True if table has at least one index column of category
    configuration
    '''
    for index in schema.ovs_tables[table].index_columns:
        if index in schema.ovs_tables[table].config:
            return True
        elif index in schema.ovs_tables[table].references:
            if schema.ovs_tables[table].references[index].category == \
                    OVSDB_SCHEMA_CONFIG:
                return True

    # no indices or no index columns with category configuration
    return False


def parseSchema(schemaFile, title=None, version=None, loadDescription=False):

    schema = RESTSchema.from_json(ovs.json.from_file(schemaFile),
                                  loadDescription)

    if title is None:
        title = schema.name
    if version is None:
        version = 'UNKNOWN'

    # add mutable flag to OVSTable
    for name, table in schema.ovs_tables.iteritems():
        table.mutable = not is_immutable(name, schema)

    return schema


def usage():
    print '''\
%(argv0)s: REST API meta schema file parser
Parse the meta schema file based on OVSDB schema to obtain category and
relation information for each REST resource.
usage: %(argv0)s [OPTIONS] SCHEMA
where SCHEMA is an extended OVSDB schema in JSON format.

The following options are also available:
  --title=TITLE               use TITLE as title instead of schema name
  --version=VERSION           use VERSION to display on document footer
  -h, --help                  display this help message\
''' % {'argv0': sys.argv[0]}
    sys.exit(0)


if __name__ == '__main__':
    try:
        try:
            options, args = getopt.gnu_getopt(sys.argv[1:], 'h',
                                              ['title=', 'version=', 'help'])
        except getopt.GetoptError, geo:
            sys.stderr.write('%s: %s\n' % (sys.argv[0], geo.msg))
            sys.exit(1)

        title = None
        version = None
        for key, value in options:
            if key == '--title':
                title = value
            elif key == '--version':
                version = value
            elif key in ['-h', '--help']:
                usage()
            else:
                sys.exit(0)

        if len(args) != 1:
            sys.stderr.write('Exactly 1 non-option arguments required '
                             '(use --help for help)\n')
            sys.exit(1)

        schema = parseSchema(args[0])

        print('Groups: ')
        for group, doc in schema.groups_doc.iteritems():
            print('%s: %s' % (group, doc))

        for table_name, table in schema.ovs_tables.iteritems():
            print('Table %s: ' % table_name)
            print('Parent  = %s' % table.parent)
            print('Description = %s' % table.desc)
            print('Configuration attributes: ')
            for column_name, column in table.config.iteritems():
                print('Col name = %s: %s' % (column_name,
                      'plural' if column.is_list else 'singular'))
                print('n_min = %d: n_max = %d' % (column.n_min, column.n_max))
                print('key type = %s: min = %s, max = %s' % (column.type,
                      column.rangeMin, column.rangeMax))
                print('key enum = %s' % column.enum)
                print('key emptyValue = %s' % column.emptyValue)
                print('key keyname = %s' % column.keyname)
                print('key kvs = %s' % column.kvs)
                if column.value_type is not None:
                    print('value type = %s: min = %s, max = %s' %
                          (column.value_type,
                           column.valueRangeMin,
                           column.valueRangeMax))
            print('Status attributes: ')
            for column_name, column in table.status.iteritems():
                print('Col name = %s: %s' % (column_name,
                      'plural' if column.is_list else 'singular'))
                print('n_min = %d: n_max = %d' % (column.n_min, column.n_max))
                print('key type = %s: min = %s, max = %s' %
                      (column.type, column.rangeMin, column.rangeMax))
                if column.value_type is not None:
                    print('value type = %s: min = %s, max = %s' %
                          (column.value_type,
                           column.valueRangeMin,
                           column.valueRangeMax))
            print('Stats attributes: ')
            for column_name, column in table.stats.iteritems():
                print('Col name = %s: %s' % (column_name,
                      'plural' if column.is_list else 'singular'))
                print('n_min = %d: n_max = %d' % (column.n_min, column.n_max))
                print('key type = %s: min = %s, max = %s' %
                      (column.type, column.rangeMin, column.rangeMax))
                if column.value_type is not None:
                    print('value type = %s: min = %s, max = %s' %
                          (column.value_type,
                           column.valueRangeMin,
                           column.valueRangeMax))
            print('Subresources: ')
            for column_name, column in table.references.iteritems():
                print('Col name = %s: %s, %s, keyname=%s' %
                      (column_name, column.relation,
                       'plural' if column.is_plural else 'singular',
                       column.keyname))
            print('\n')

    except error.Error, e:
        sys.stderr.write('%s: %s\n' % (e.msg, e.json))
        sys.exit(1)

# Local variables:
# mode: python
# End:
