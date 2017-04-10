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

import ovs.db.idl
import json
from tornado.locks import Event


class OvsdbTransactionList:
    def __init__(self):
        self.txn_list = []

    def add_txn(self, txn):
        self.txn_list.append(txn)


class OvsdbTransaction:
    def __init__(self, idl):
        self.status = None
        self.txn = ovs.db.idl.Transaction(idl)
        self.event = Event()

    def commit(self):
        self.status = self.txn.commit()
        return self.status

    def insert(self, table):
        return self.txn.insert(table)

    def abort(self):
        if self.txn is not None:
            self.txn.abort()

    def get_error(self):
        return json.loads(self.txn.get_error())


class OvsdbTransactionResult:
    def __init__(self, status, index=None):
        self.status = status
        self.index = index
