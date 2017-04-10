OPS-RESTD
===================
What is ops-restd?
----------------------
The ops-restd is a module that provides REST API access to OpenSwitch's OVSDB database. It's an application written using Python using the Tornado (www.tornado.org) web framework and d
oes the following:

 - Runs an HTTP server that listens to incoming HTTPS requests on port 443.
 - Runs the REST API application that provides read/write access to the OVSDB database.

What is the structure of the repository?
----------------------------------------------
Refer to the GIT repository at http://git.openswitch.net/cgit/openswitch/ops-restd/ to find more about the ``ops-restd``` module and the Python modules it provides.

What is the license?
------------------------
(c) Copyright 2015 Hewlett Packard Enterprise Development LP.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
