OpenSwitch RESTful API to OVSDB
===================

Overview
------------
OpenSwitch provides a Tornado framework-based application to access **OVSDB** using RESTful APIs. The ops-restd module provides all the necessary python packages required to add, delete, modify tables in the OVSDB database using ```HTTP``` methods, ```GET, POST, PUT and DELETE```.

Modules
------
The ops-restd module consists of the following:

 - The **opslib** module is the interface to the OVSDB schema and OpenSwitch extended schema.
 - The **opsrest** module is the Tornado application to provide RESTful access to OVSDB.
 - The **runconfig** module loads a user-defined OVSDB configuration.

The ```opslib``` module provides the following:
- Interface to OpenSwitch's vswitch.extschema and vswitch.xml files.
- Tools to automatically generate documentation of all supported APIs.

The database schema and the relationship between various tables is defined by these two files and opslib captures this information. The ```opsrest``` module uses this information to verify the REST APIs and to allow or deny access to the resources (tables) in the database. This module is also used to generate the Swagger documentation of the APIs that are supported by ```ops-restd```

```
opslib
├── apidocgen.py (**creates Swagger documentation of supported APIs**)
├── \__init__.py
└── restparser.py (**interface to vswitch.extschema and vswitch.xml**)

```

The ```opsrest``` module is the implementation of the RESTful API application and perfoms the following tasks:

 - Maintains a persistent connection with the OVSDB server.
 - Actively listens to notifications from the OVSDB server to monitor changes to the OVSDB.
 - Asynchronously accepts and serves incoming HTTP requests.
 - Provides GET/POST/PUT/DELETE HTTP methods to read/add/modify/delete resources in the OVSDB database.
 - Provides authentication and authorization feature for the APIs.


```
opsrest
├── application.py
├── constants.py
├── delete.py
├── get.py
├── handlers
│   ├── base.py
│   ├── config.py
│   └── \__init__.py
├── \__init__.py
├── manager.py
├── parse.py
├── post.py
├── put.py
├── resource.py
├── settings.py
├── transaction.py
├── urls.py
├── utils
│   ├── \__init__.py
│   └── utils.py
└── verify.py
```

The ```runconfig``` module provides the functionality to save a user-defined OpenSwitch configuration to the OVSDB.
The ```opslib``` and the ```ops-cli``` modules use ```runconfig``` to allow REST and cLI access to this feature.

```
runconfig
├── \__init__.py
├── runconfig.py
├── settings.py
└── startupconfig.py
```

Design
------------------
The ```ops-restd``` module uses the Tornado non-blocking feature to implement an asynchronous application that simultaneously accepts more than one HTTP connection and performs non-blocking read/write funciton to the OVSDB.

The ```Python``` class ```OvsdbConnectionManager``` found in ```opsrest/manager.py``` provides all the connection, read, write related features with OVSDB.

The ```OvsdbConnectionManager``` maintains a list of all OVSDB transactions in a ```OvsdbTransactionList``` object. Each transaction corresponds to a write request to the database.
```
            if self.transactions is None:
                self.transactions = OvsdbTransactionList()
```
On every IOLoop iteration the transactions in this list are checked to their current status. If a transaction is ```INCOMPLETE```, a ```commit``` is called on it and in all other cases it is removed from the transaction list and the method invoking it is notified.
```
    def check_transactions(self):

        for item in self.transactions.txn_list:
            item.commit()

        count = 0
        for item in self.transactions.txn_list:

            # TODO: Handle all states
            if item.status is not INCOMPLETE:
                self.transactions.txn_list.pop(count)
                item.event.set()
            else:
                count += 1
```
