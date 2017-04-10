# Full Declarative Configuration

## Contents
- [Overview](#overview)
- [Modules](#modules)
- [Usage](#usage)

## Overview
Declarative configuration is used for reading and writing full configuration data into OVSDB.

The ```runconfig``` module  provides the functionality to save a user-defined OpenSwitch full configuration to OVSDB, or to read the full configuration data from OVSDB.  Declarative Configuration is invoked by the REST API's GET/PUT full configuration request. See the example in Usage for details.

There are two types of configurations, the current "running" configuration and the "startup" configuration. The running configuration does not persist across reboots, whereas the startup configuration does.  When a configuration is "saved", such that it persists across reboots, it is stored in the "configuration" table in OVSDB (configtbl).

## Modules
The ```runconfig``` module is part of  ```ops-restd``` repo. It has the following modules:
```
runconfig
    - __init__.py
    - runconfig.py
    - settings.py
    - declarativeconfig.py
    - validatoradapter.py
    - startupconfig.py
```

### startupconfig.py
The ```startupconfig.py``` module is used to load the switch with the initial configuration on boot up.

OVSDB is not persistent across reboots, so it initially comes up empty, except for the configurations table (configtbl). After the platform daemons have discovered all of the present hardware, and populated the OVSDB with the relevant information for the hardware, the configuration daemon (cfgd) looks into the configtbl table to see if any saved configuration exists. The cfgd daemon looks for a startup type entry. If a startup configuration is found, it is applied over the rest of the tables. Otherwise, the cfgd daemon notes that no configuration file was found.

### runconfig.py
The ```runconfig.py``` wrapper invokes the read and write functions in the ```declarativeconfig.py``` module.

### declarativeconfig.py
The ```declarativeconfig.py``` module contains read and write functions which are invoked by ```runconfig.py```.

When a user sends a GET request, the read function is invoked from REST handlers, and works as follows: The function reads OVSDB, table by table, and populates the JSON data (content of the GET response) with all of the columns that are of type configuration.

When a user sends a PUT request, the write function is invoked, and works as follows: For all top level tables, the entries are read from JSON data and populated to OVSDB table by table. All tables under the top level table (children) are populated recursively. Immutable tables are ignored, and the rest of the tables are updated with user input configuration data. PUT is not an append, but is an overwrite operation. Existing data is replaced by the provided input and, any missing fields in the input JSON data is treated as being removed and is cleared from OVSDB. Schema validations and custom validations are performed to catch erroneous configuration input, and the erroneous input is rejected.

### validatoradapter.py
The ```validatoradapter.py``` module provides validations for resource creating, updating, and deleting. For more details, refer to ```custom_validators_design.md```.

## Usage
A user can send a GET request with a url ```https://x.x.x.x/rest/v1/system/full-configuration?type=running``` to get the running configuration of a switch.

A user can give the full configuration data, from the body of a REST API's PUT request, to update OVSDB with that configuration.

The PUT request data is in JSON data format. A basic example follows:
```
{
    "table_name": {
        "column_name": "value",
        "column_name": "value"
    }
}
```
This input data is constructed using the ```vswitch.extschema```, which is a JSON file with a list of table names, column names under each table, and the relationship between the tables.
