#!/usr/bin/env python
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from opsvsi.docker import *
from opsvsi.opsvsitest import *
from tornado import testing, websocket
from tornado.httpclient import HTTPRequest
from opsvsiutils.restutils.utils import (
    execute_request,
    get_switch_ip,
    get_ssl_context,
    get_server_crt,
    login,
    PORT_DATA,
    remove_server_crt,
    rest_sanity_check
)
from copy import deepcopy
import httplib
import json
import urllib

WS_PATH = 'rest/v1/ws/notifications'

REQUEST_TIMEOUT = 50
CONNECT_TIMEOUT = 50

SUBSCRIBER_RESPONSE = 'notification_subscriber'
SUBSCRIBER_RESOURCE = 'resource'
SUBSCRIPTION_RESOURCE = 'resource'
SUBSCRIPTION_INDEX = 'name'

NOTIF_MSG = 'notifications'
NOTIF_ADDED = 'added'
NOTIF_MODIFIED = 'modified'
NOTIF_DELETED = 'deleted'
NOTIF_VALUES = 'values'
NOTIF_NEW_VALUES = 'new_values'
NOTIF_RESOURCE = 'resource'
NOTIF_SUBSCRIPTION = 'subscription'

SUBSCRIBER_URI = '/rest/v1/system/notification_subscribers'

SUBSCRIBER_TABLE = 'Notification_Subscriber'
SUBSCRIBER_INDEX = 'name'
GET_SUBSCRIBER_CMD = 'ovsdb-client dump %s %s' % (SUBSCRIBER_TABLE,
                                                  SUBSCRIBER_INDEX)

SUBSCRIPTION_TABLE = 'Notification_Subscription'
GET_SUBSCRIPTION_CMD = 'ovsdb-client dump %s %s' % (SUBSCRIPTION_TABLE,
                                                    SUBSCRIPTION_RESOURCE)

SUBSCRIPTION_COLUMN = 'notification_subscriptions'

UPDATE_KEY = 'update_key'
UPDATE_VALUE = 'update_value'

BGP_ASN_INDEX = 6001
FORWARD_REF_ROW_CFG = {
    "configuration": {
        "always_compare_med": True,
        "asn": BGP_ASN_INDEX
    }
}
FORWARD_REF_ROW_PARENT_URI = "/rest/v1/system/vrfs/vrf_default"
FORWARD_REF_ROW_PARENT_SUB = {
    SUBSCRIPTION_INDEX: "forward_ref_row_parent",
    SUBSCRIPTION_RESOURCE: FORWARD_REF_ROW_PARENT_URI
}
FORWARD_REF_ROW_SUB_POST_URI = FORWARD_REF_ROW_PARENT_URI + '/' + "bgp_routers"
FORWARD_REF_ROW_SUB_URI = "%s/%s" % (FORWARD_REF_ROW_SUB_POST_URI,
                                     BGP_ASN_INDEX)
FORWARD_REF_ROW_SUB = {
    SUBSCRIPTION_INDEX: "forward_ref_row_sub",
    SUBSCRIPTION_RESOURCE: FORWARD_REF_ROW_SUB_URI
}
FORWARD_REF_COLL_SUB_URI = FORWARD_REF_ROW_SUB_POST_URI
FORWARD_REF_COLL_SUB = {
    SUBSCRIPTION_INDEX: "forward_ref_coll_sub",
    SUBSCRIPTION_RESOURCE: FORWARD_REF_COLL_SUB_URI
}

ROUTE = '10.0.0.0/8'
ROUTE_URL_SAFE = urllib.quote_plus(ROUTE)
NEXT_HOP = '10.0.0.1'
NEXT_HOP2 = '10.0.0.2'
BACK_REF_ROW_SUB_POST_URI = "/rest/v1/system/vrfs/vrf_default/routes"
BACK_REF_ROW_SUB_URI = "%s/%s/%s" % (BACK_REF_ROW_SUB_POST_URI, 'static',
                                     ROUTE_URL_SAFE)
BACK_REF_ROW_SUB = {
    SUBSCRIPTION_INDEX: "back_ref_row_sub",
    SUBSCRIPTION_RESOURCE: BACK_REF_ROW_SUB_URI
}

BACK_REF_COLL_SUB_URI = BACK_REF_ROW_SUB_POST_URI
BACK_REF_COLL_SUB = {
    SUBSCRIPTION_INDEX: "back_ref_coll_sub",
    SUBSCRIPTION_RESOURCE: BACK_REF_COLL_SUB_URI
}

PORT_INDEX = "Port1"
TOP_LEVEL_ROW_CFG = PORT_DATA
remove_keys = ['vlan_trunks', 'vlan_tag', 'vlan_mode']
for key in remove_keys:
    if key in TOP_LEVEL_ROW_CFG['configuration']:
        del TOP_LEVEL_ROW_CFG['configuration'][key]

TOP_LEVEL_ROW_SUB_POST_URI = "/rest/v1/system/ports"
TOP_LEVEL_ROW_SUB_URI = "%s/%s" % (TOP_LEVEL_ROW_SUB_POST_URI, PORT_INDEX)
TOP_LEVEL_ROW_SUB = {
    SUBSCRIPTION_INDEX: "top_level_row_sub",
    SUBSCRIPTION_RESOURCE: TOP_LEVEL_ROW_SUB_URI
}
TOP_LEVEL_COLL_SUB_URI = TOP_LEVEL_ROW_SUB_POST_URI
TOP_LEVEL_COLL_SUB = {
    SUBSCRIPTION_INDEX: "top_level_coll_sub",
    SUBSCRIPTION_RESOURCE: TOP_LEVEL_COLL_SUB_URI
}


class WebSocketEventTest(OpsVsiTest):
    def setupNet(self):
        self.net = Mininet(topo=SingleSwitchTopo(k=0, hopts=self.getHostOpts(),
                                                 sopts=self.getSwitchOpts()),
                           switch=VsiOpenSwitch,
                           host=Host,
                           link=OpsVsiLink,
                           controller=None,
                           build=True)

        self.switch = self.net.switches[0]
        self.switch_ip = get_switch_ip(self.switch)

@pytest.mark.skipif(True, reason="fix nginx conf to support websockets")
class TestWebSocketEvents(testing.AsyncTestCase):
    def setup(self):
        pass

    def setUp(self):
        super(TestWebSocketEvents, self).setUp()

    def teardown(self):
        pass

    def setup_class(cls):
        TestWebSocketEvents.test_var = WebSocketEventTest()
        cls.switch_ip = cls.test_var.switch_ip
        cls.switch = cls.test_var.switch
        get_server_crt(cls.switch)
        rest_sanity_check(cls.switch_ip)
        cls.cookie_header = login(cls.switch_ip)

    def teardown_class(cls):
        TestWebSocketEvents.test_var.net.stop()
        remove_server_crt()

    def setup_method(self, method):
        sleep(2)
        pass

    def teardown_method(self, method):
        pass

    def __del__(self):
        del self.test_var

    def create_ws_connection(cls):
        ws_uri = 'wss://%s/%s' % (cls.test_var.switch_ip, WS_PATH)
        info("### Creating connection to %s ###\n" % ws_uri)

        # Add additional info for HTTPS
        ssl_context = get_ssl_context()
        http_request = HTTPRequest(url=ws_uri,
                                   headers=cls.cookie_header,
                                   connect_timeout=CONNECT_TIMEOUT,
                                   request_timeout=REQUEST_TIMEOUT,
                                   follow_redirects=True,
                                   ssl_options=ssl_context)

        return websocket.websocket_connect(http_request)

    def get_subscriber_uri(self, connection_response):
        assert SUBSCRIBER_RESPONSE in connection_response and \
            SUBSCRIBER_RESOURCE in connection_response[SUBSCRIBER_RESPONSE], \
            "Invalid connection response"

        sub_uri = connection_response[SUBSCRIBER_RESPONSE][SUBSCRIBER_RESOURCE]
        info("### Received subscriber URI: %s ###\n" % sub_uri)
        return sub_uri

    def subscribe_and_check(self, subscriber_uri, subscription_data,
                            check_success=True, get_response=False):
        resource = subscription_data[SUBSCRIPTION_RESOURCE]
        subscription_post_uri = subscriber_uri + '/' + SUBSCRIPTION_COLUMN
        subscription_uri = "%s/%s" % (subscription_post_uri,
                                      subscription_data[SUBSCRIPTION_INDEX])
        info("### Subscribing to %s ###\n" % resource)
        info("### Subscription POST URI %s ###\n" % subscription_post_uri)
        info("### Subscription URI %s ###\n" % subscription_uri)

        # Wrap the subscription_data in 'configuration'
        config_data = {"configuration": subscription_data}
        status_code, response_body = \
            execute_request(subscription_post_uri,
                            "POST",
                            json.dumps(config_data),
                            self.switch_ip,
                            xtra_header=self.cookie_header)

        if check_success:
            assert status_code == httplib.CREATED, \
                "Creation of subscription failed. Status: %s" % status_code
        else:
            assert status_code == httplib.BAD_REQUEST, \
                "Creation of subscription unexpectedly successful."

        if get_response:
            return subscription_uri, response_body
        else:
            return subscription_uri

    def check_subscriber_in_db(self, response_data, check_is_in=True):
        sub_uri = self.get_subscriber_uri(response_data)
        sub_name = sub_uri.split('/')[-1]
        subs_in_db = self.switch.cmd(GET_SUBSCRIBER_CMD)

        if check_is_in:
            info("### Verifying subscriber %s is in DB ###\n" % sub_name)
            assert sub_name in subs_in_db, "Subscriber not found in DB."
            info("### Subscriber found in DB. ###\n")
        else:
            info("### Verifying subscriber %s is not in DB ###\n" % sub_name)
            assert sub_name not in subs_in_db, "Subscriber found in DB."
            info("### Subscriber not found in DB. ###\n")

        return sub_name, sub_uri

    def verify_notification_msg(self, notification_msg, notif_type,
                                resource_uri, subscription_uri):
        info("### Verifying notification message type '%s': ###\n" %
             notif_type)
        info("%s\n" % notification_msg)

        assert NOTIF_MSG in notification_msg, "Invalid notification message"
        if notif_type == NOTIF_ADDED:
            assert NOTIF_ADDED in notification_msg[NOTIF_MSG] and \
                NOTIF_VALUES in notification_msg[NOTIF_MSG][NOTIF_ADDED][0], \
                "Invalid added notification message"
        elif notif_type == NOTIF_MODIFIED:
            assert NOTIF_MODIFIED in notification_msg[NOTIF_MSG] and \
                NOTIF_NEW_VALUES in \
                notification_msg[NOTIF_MSG][NOTIF_MODIFIED][0], \
                "Invalid modified notification message"
        else:
            assert NOTIF_DELETED in notification_msg[NOTIF_MSG], \
                "Invalid deleted notification message"

        found = False
        for notification in notification_msg[NOTIF_MSG][notif_type]:
            rcvd_resource_uri = notification[NOTIF_RESOURCE]
            rcvd_subscription_uri = notification[NOTIF_SUBSCRIPTION]

            info("### Verifying subscription URIs ###\n")
            info("### Actual subscription URI: %s ###\n" % subscription_uri)
            info("### Received subscription URI: %s ###\n" %
                 rcvd_subscription_uri)
            if subscription_uri == rcvd_subscription_uri:
                resource_uri_segments = resource_uri.split('/')
                rcvd_resource_uri_segments = rcvd_resource_uri.split('/')

                # Compare the URI segments. Comparing segments to be forward
                # compatible for wildcards. All of the original resource URI
                # should be in the received resource URI for row and
                # collection subscriptions.
                for index, segment in enumerate(resource_uri_segments):
                    if segment != rcvd_resource_uri_segments[index]:
                        break

                found = True

        assert found, "Notification message did not match the subscription"
        info("### Notification message verified ###\n")

    def retrieve_resource_values(self, resource_uri):
        info("### Obtaining resource data via GET ###\n")
        status_code, response = execute_request(resource_uri, "GET", None,
                                                self.switch_ip,
                                                xtra_header=self.cookie_header)

        assert status_code == httplib.OK, \
            "Unable to get resource data. Status: %s" % status_code

        get_data = json.loads(response)
        resource_values = []

        # Remove categories from the GET response
        if isinstance(get_data, list):
            info("### Getting values for a collection ###\n")

            for uri in get_data:
                info("### Obtaining values for %s ###\n" % uri)
                resource_values.append(self.retrieve_resource_values(uri)[0])
        else:
            info("### Getting values for a row ###\n")
            get_values = {}
            for category, values in get_data.iteritems():
                # Strip statistics and status since those may change and not
                # match. It makes the test case too error prone.
                if category == 'configuration':
                    get_values.update(values)

            resource_values.append(get_values)

        return resource_values

    def compare_values(self, superset, subset):
        info("### Comparing values between superset and subset ###\n")
        info("### Values from superset: ###\n")
        info("%s\n" % superset)
        info("### Values from subset: ###\n")
        info("%s\n" % subset)
        return all(item in superset.items() for item in subset.items())

    def verify_subscription_initial_values(self, notification, resource_uri,
                                           subscription_uri):
        info("### Verifying subscription initial values from "
             "notification ###\n")
        self.verify_notification_msg(notification, NOTIF_ADDED, resource_uri,
                                     subscription_uri)

        notif_values_list = []
        db_values_list = []

        for initial_values in notification[NOTIF_MSG][NOTIF_ADDED]:
            notif_values_list.append(initial_values[NOTIF_VALUES])

        db_values_list = self.retrieve_resource_values(resource_uri)

        info("### Values from notification: ###\n")
        info("%s\n" % notif_values_list)
        info("### Values from DB ###\n")
        info("%s\n" % db_values_list)

        assert len(db_values_list) == len(notif_values_list), \
            "Mismatching number of notifications"

        found = False
        for notif_values in notif_values_list:
            for db_values in db_values_list:
                # Since DB values exclude status/statistics, it will be
                # considered as the subset, which is passed as the second
                # argument to the compare_values function.
                if self.compare_values(notif_values, db_values):
                    found = True
                    break

        assert found, "Initial values not matching"

    def verify_modified_notification(self, notification, resource_uri,
                                     subscription_uri, update_cfg):
        info("### Verifying modified notification ###\n")
        self.verify_notification_msg(notification, NOTIF_MODIFIED,
                                     resource_uri, subscription_uri)

        # Since it's a row subscription, only one notification. Get first idx.
        values = notification[NOTIF_MSG][NOTIF_MODIFIED][0][NOTIF_NEW_VALUES]
        update_data = update_cfg["configuration"]

        info("### Comparing received new values against update data ###\n")
        info("### New values from notification: ###\n")
        info("%s\n" % values)
        info("### Values from update data: ###\n")
        info("%s\n" % update_data)
        assert all(item in values.items() for item in update_data.items()), \
            "New values do not contain the update values"

        info("### Modified values verified ###\n")

    def test_subscriber_invalid_add_through_rest(self):
        info("\n########## Testing invalid add of subscriber "
             "through REST ##########\n")
        info("### Attempting to add subscriber through POST ###\n")
        subscriber_data = {
            "configuration": {
                "name": "test_subscriber",
                "type": "ws"
            }
        }

        status_code, response = execute_request(SUBSCRIBER_URI, "POST",
                                                json.dumps(subscriber_data),
                                                self.switch_ip,
                                                xtra_header=self.cookie_header)
        assert status_code == httplib.BAD_REQUEST, \
            "Adding subscriber unexpectedly successful."

        assert '10005' in response or 'prohibited' in response, \
            "Expected error not found in response"

        info("### Invalid adding of websocket subscriber verified. ###\n")

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscriber_invalid_ws_remove_through_rest(self):
        info("\n########## Testing invalid removal of a websocket subscriber "
             "through REST ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        sub_uri = self.get_subscriber_uri(response_data)

        info("### Attempting to delete subscriber through REST ###\n")
        status_code, response = execute_request(sub_uri, "DELETE", None,
                                                self.switch_ip,
                                                xtra_header=self.cookie_header)

        assert status_code == httplib.BAD_REQUEST, \
            "Deleting subscriber unexpectedly successful."

        assert '10005' in response or 'prohibited' in response, \
            "Expected error not found in response"

        info("### Invalid deleting of websocket subscriber verified. ###\n")
        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_websocket_connect_and_subscriber_inserted(self):
        """
        Test to verify that a websocket connect results in a new subscriber
        is added successfully in the DB.
        """
        info("\n########## Testing websocket connect ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.check_subscriber_in_db(response_data)
        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_websocket_disconnect_cleans_subscriber_data(self):
        """
        Test to verify that a websocket subscriber is removed upon disconnect.
        """
        info("\n########## Testing websocket disconnect "
             "and cleaned ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        self.check_subscriber_in_db(response_data)

        info("### Closing websocket connection ###\n")
        conn.close()

        self.check_subscriber_in_db(response_data, False)

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_websocket_disconnect_clean_subscription_data(self):
        """
        Test to verify that a websocket subscriber disconnect results in
        subscriptions being cleaned.
        """
        info("\n########## Testing websocket disconnect "
             "and cleaned ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding subscription ###\n")
        subscription_data = FORWARD_REF_COLL_SUB
        self.subscribe_and_check(subscriber_uri, subscription_data)

        info("### Closing websocket connection ###\n")
        conn.close()

        self.check_subscriber_in_db(response_data, False)

        info("### Verify Subscription is removed from the DB ###\n")
        subscription_resource = subscription_data[SUBSCRIPTION_RESOURCE]
        subscriptions_in_db = self.switch.cmd(GET_SUBSCRIPTION_CMD)

        assert subscription_resource not in subscriptions_in_db, \
            "Subscription not removed from DB."

        info("### Subscription successfully removed from DB ###\n")

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_forward_ref(self):
        """
        Test to verify subscribing to a forward reference row will notify
        with the initial values of the resource.
        """
        info("\n########## Testing subscription to forward reference "
             "row and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref child ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_ROW_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                FORWARD_REF_ROW_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_forward_ref_modified(self):
        """
        Test to verify notification when a forward ref resource is modified.
        """
        info("\n########## Testing notification for a forward reference "
             "row when modified ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref child ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Modifying resource to trigger notification ###\n")
        update_cfg = {
            "configuration": {
                "always_compare_med": False
            }
        }

        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI, "PUT",
                                         json.dumps(update_cfg),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)
        assert status_code == httplib.OK, \
            "Update failed. Status: %s\n" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_modified_notification(response_data,
                                          FORWARD_REF_ROW_SUB_URI,
                                          subscription_uri, update_cfg)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_forward_ref_deleted(self):
        """
        Test to verify notification when a forward ref resource is deleted.
        """
        info("\n########## Testing notification for a forward reference "
             "row when deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref child ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     FORWARD_REF_ROW_SUB_URI,
                                     subscription_uri)

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_backward_ref(self):
        """
        Test to verify subscribing to a backward reference row will notify
        with the initial values of the resource.
        """
        info("\n########## Testing subscription to backward reference "
             "row and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a backward reference resource to monitor ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))
        self.switch.cmdCLI('end')

        info("### Subscribing to backward ref child ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    BACK_REF_ROW_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                BACK_REF_ROW_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_backward_ref_modified(self):
        """
        Test to verify notification when a backward ref resource is modified.
        """
        info("\n########## Testing notification for a backward reference "
             "row when modified ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a backward reference resource to monitor ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))

        info("### Subscribing to backward ref child ###\n")
        self.subscribe_and_check(subscriber_uri, BACK_REF_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Modifying resource to trigger notification ###\n")
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP2))
        self.switch.cmdCLI('end')

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        # Since it's a row subscription, only one notification. Get first idx.
        info("### Verifying modified notification ###\n")
        values = response_data[NOTIF_MSG][NOTIF_MODIFIED][0][NOTIF_NEW_VALUES]
        db_values = self.retrieve_resource_values(BACK_REF_ROW_SUB_URI)[0]
        self.compare_values(db_values, values)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_backward_ref_deleted(self):
        """
        Test to verify notification when a backward ref resource is deleted.
        """
        info("\n########## Testing notification for a backward reference "
             "row when deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a backward reference resource to monitor ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))
        self.switch.cmdCLI('end')

        info("### Subscribing to backward ref child ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    BACK_REF_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     BACK_REF_ROW_SUB_URI,
                                     subscription_uri)

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_top_level(self):
        """
        Test to verify subscribing to a top-level row will notify
        with the initial values of the resource.
        """
        info("\n########## Testing subscription to a top-level "
             "row and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a top-level resource to monitor ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        info("### Subscribing to top-level row ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_ROW_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                TOP_LEVEL_ROW_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_top_level_modified(self):
        """
        Test to verify notification when a top-level resource is modified.
        """
        info("\n########## Testing notification for a top-level "
             "row when modified ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a top-level resource to monitor ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        info("### Subscribing to top-level row ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Modifying resource to trigger notification ###\n")
        update_cfg = {
            "configuration": {
                "external_ids": {
                    "test_key": "test_value"
                }
            }
        }

        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI, "PUT",
                                         json.dumps(update_cfg),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)
        assert status_code == httplib.OK, \
            "Update failed. Status: %s\n" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_modified_notification(response_data,
                                          TOP_LEVEL_ROW_SUB_URI,
                                          subscription_uri, update_cfg)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()


    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_row_top_level_deleted(self):
        """
        Test to verify notification when a top-level resource is deleted.
        """
        info("\n########## Testing notification for a top-level "
             "row when deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a top-level resource to monitor ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        info("### Subscribing to top-level row ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     TOP_LEVEL_ROW_SUB_URI,
                                     subscription_uri)

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_forward_refs(self):
        """
        Test to verify subscribing to a forward reference collection will
        notify with the initial values of the resource.
        """
        info("\n########## Testing subscription to forward reference "
             "collection and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_COLL_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                FORWARD_REF_COLL_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_forward_refs_added(self):
        """
        Test to verify subscribing to a forward reference collection will
        notify when a resource is added into the monitored collection.
        """
        info("\n########## Testing subscription to a forward reference "
             "collection and a row is added ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Subscribing to forward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_COLL_SUB)

        info("### Adding a forward reference row to trigger "
             "notification ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                FORWARD_REF_COLL_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_forward_refs_deleted(self):
        """
        Test to verify subscribing to a forward reference collection will
        notify when a resource is deleted from the monitored collection.
        """
        info("\n########## Testing subscription to a forward reference "
             "collection and a row is deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    FORWARD_REF_COLL_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     FORWARD_REF_COLL_SUB_URI,
                                     subscription_uri)

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_backward_refs(self):
        """
        Test to verify subscribing to a backward reference collection will
        notify with the initial values of the resource.
        """
        info("\n########## Testing subscription to backward reference "
             "collection and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a backward reference resource to monitor ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))
        self.switch.cmdCLI('end')

        info("### Subscribing to backward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    BACK_REF_COLL_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                BACK_REF_COLL_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_backward_refs_added(self):
        """
        Test to verify subscribing to a backward reference collection will
        notify when a resource is added into the monitored collection.
        """
        info("\n########## Testing subscription to a backward reference "
             "collection and a row is added ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Subscribing to backward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    BACK_REF_COLL_SUB)

        info("### Adding a backward reference row to trigger "
             "notification ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))
        self.switch.cmdCLI('end')

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                BACK_REF_COLL_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_backward_refs_deleted(self):
        """
        Test to verify subscribing to a backward reference collection will
        notify when a resource is deleted from the monitored collection.
        """
        info("\n########## Testing subscription to a backward reference "
             "collection and a row is deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a backward reference row to monitor ###\n")
        self.switch.cmdCLI('configure terminal')
        self.switch.cmdCLI('ip route %s %s' % (ROUTE, NEXT_HOP))
        self.switch.cmdCLI('end')

        info("### Subscribing to backward ref collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    BACK_REF_COLL_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(BACK_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     BACK_REF_COLL_SUB_URI,
                                     subscription_uri)

        conn.close()


    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_top_level(self):
        """
        Test to verify subscribing to a top-level collection will notify
        with the initial values of the resource.
        """
        info("\n########## Testing subscription to a top-level "
             "collection and initial values ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a top-level resource to monitor ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        info("### Subscribing to top-level collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_COLL_SUB)

        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                TOP_LEVEL_COLL_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()


    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_top_level_added(self):
        """
        Test to verify subscribing to a top-level collection will
        notify when a resource is added into the monitored collection.
        """
        info("\n########## Testing subscription to a top-level "
             "collection and a row is added ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Subscribing to top-level collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_COLL_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Adding a top-level row to trigger notification ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_subscription_initial_values(response_data,
                                                TOP_LEVEL_ROW_SUB_URI,
                                                subscription_uri)

        info("### Cleaning created resource ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        conn.close()


    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_to_collection_top_level_deleted(self):
        """
        Test to verify subscribing to a top-level collection will
        notify when a resource is deleted from the monitored collection.
        """
        info("\n########## Testing subscription to a top-level "
             "collection and a row is deleted ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a top-level resource to monitor ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_POST_URI, "POST",
                                         json.dumps(TOP_LEVEL_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added top-level resource ###\n")
        info("### Subscribing to top-level collection ###\n")
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    TOP_LEVEL_COLL_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(TOP_LEVEL_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     TOP_LEVEL_COLL_SUB_URI,
                                     subscription_uri)

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_multiple_subscribers_notification(self):
        """
        Test to verify notification is sent for multiple subscribers that
        subscribed to the same resource.
        """
        info("\n########## Testing notification for multiple "
             "subscribers ##########\n")
        sub1_conn = yield self.create_ws_connection()
        sub2_conn = yield self.create_ws_connection()

        response = yield sub1_conn.read_message()
        response_data = json.loads(response)
        _, subscriber1_uri = self.check_subscriber_in_db(response_data)

        response = yield sub2_conn.read_message()
        response_data = json.loads(response)
        _, subscriber2_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a forward reference resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added forward reference resource ###\n")
        info("### Subscribing to forward ref child for subscriber 1 ###\n")
        subscription1_uri = self.subscribe_and_check(subscriber1_uri,
                                                     FORWARD_REF_ROW_SUB)
        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield sub1_conn.read_message()

        info("### Subscribing to forward ref child for subscriber 2 ###\n")
        subscription2_uri = self.subscribe_and_check(subscriber2_uri,
                                                     FORWARD_REF_ROW_SUB)
        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield sub2_conn.read_message()

        info("### Deleting resource to trigger notification ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process for "
             "subscriber 1 ###\n")
        response = yield sub1_conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     FORWARD_REF_ROW_SUB_URI,
                                     subscription1_uri)
        sub1_conn.close()

        info("### Retrieve notification message and process for "
             "subscriber 2 ###\n")
        response = yield sub2_conn.read_message()
        response_data = json.loads(response)

        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     FORWARD_REF_ROW_SUB_URI,
                                     subscription2_uri)
        sub2_conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_invalid_resource(self):
        """
        Test to verify subscribing to an invalid resource will return an error.
        """
        info("\n########## Testing subscription to an "
             "invalid resource ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Subscribing to non-existent resource ###\n")
        _, response = self.subscribe_and_check(subscriber_uri,
                                               FORWARD_REF_ROW_SUB,
                                               False, True)

        assert '10001' in response or 'Invalid' in response, \
            "Expected error not found in response"

        info("### Subscription to invalid resource URI verified ###\n")
        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_duplicate_resource(self):
        """
        Test to verify subscribing to the same resource will return an error.
        """
        info("\n########## Testing duplicate subscription to a "
             "resource ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Subscribing to a resource ###\n")
        subscription = FORWARD_REF_COLL_SUB
        subscription_uri = self.subscribe_and_check(subscriber_uri,
                                                    subscription)

        info("### Subscribing to the same resource in a new "
             "subscription ###\n")
        new_subscription = deepcopy(subscription)
        new_subscription[SUBSCRIPTION_INDEX] = "duplicate_subscription"
        subscription_uri, response = self.subscribe_and_check(subscriber_uri,
                                                              new_subscription,
                                                              False, True)

        info("### Verifying response contains an error ###\n")
        assert '10006' in response or 'redundant' in response, \
            "Expected error not found in response"

        conn.close()

    @testing.gen_test(timeout=REQUEST_TIMEOUT)
    def test_subscribe_multiple_resources_modified(self):
        """
        Test to verify subscribing to multiple resources and receiving
        notifications for both subscriptions.
        """
        info("\n########## Testing subscription to multiple "
             "resources ##########\n")
        conn = yield self.create_ws_connection()
        response = yield conn.read_message()
        response_data = json.loads(response)
        _, subscriber_uri = self.check_subscriber_in_db(response_data)

        info("### Adding a resource to monitor ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_POST_URI, "POST",
                                         json.dumps(FORWARD_REF_ROW_CFG),
                                         self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.CREATED, \
            "Creation of forward ref failed. Status: %s" % status_code

        info("### Successfully added resource ###\n")
        info("### Subscribing to forward ref child ###\n")
        child_sub_uri = self.subscribe_and_check(subscriber_uri,
                                                 FORWARD_REF_ROW_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Subscribing to the parent of the forward ref child ###\n")
        parent_sub_uri = self.subscribe_and_check(subscriber_uri,
                                                  FORWARD_REF_ROW_PARENT_SUB)

        # Get the initial notification message that is sent upon subscribing
        # and discard it.
        response = yield conn.read_message()

        info("### Deleting the child resource to trigger a notification "
             " for both subscriptions ###\n")
        status_code, _ = execute_request(FORWARD_REF_ROW_SUB_URI,
                                         "DELETE", None, self.switch_ip,
                                         xtra_header=self.cookie_header)

        assert status_code == httplib.NO_CONTENT, \
            "Unable to delete resource. Status: %s" % status_code

        info("### Retrieve notification message and process ###\n")
        response = yield conn.read_message()
        response_data = json.loads(response)

        info("### Verifying received deleted notification for "
             "subscription to child ###\n")
        self.verify_notification_msg(response_data, NOTIF_DELETED,
                                     FORWARD_REF_ROW_SUB_URI,
                                     child_sub_uri)

        # Construct a configuration that represents deletion of a bgp_router
        # which is used for verifying the modification notification.
        update_cfg = {
            "configuration": {
                "bgp_routers": {}
            }
        }
        info("### Verifying received modified notification for "
             "subscription to parent ###\n")
        self.verify_modified_notification(response_data,
                                          FORWARD_REF_ROW_PARENT_URI,
                                          parent_sub_uri, update_cfg)

        conn.close()
