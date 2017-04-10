
# [Standard REST API] Test Cases
## Contents

- [REST full declarative configuration](#rest-full-declarative-configuration)
- [Notifications test cases](#notifications-test-cases)
  - [Add invalid WebSocket subscriber through REST](#add-invalid-websocket-subscriber-through-rest)
  - [Invalid deletion of WebSocket subscriber through REST](#invalid-deletion-of-websocket-subscriber-through-rest)
  - [WebSocket connect and subscriber created](#websocket-connect-and-subscriber-created)
  - [WebSocket disconnect cleans subscriber data](#websocket-disconnect-cleans-subscriber-data)
  - [WebSocket disconnect cleans subscription data](#websocket-disconnect-cleans-subscription-data)
  - [Subscribe to forward reference row](#subscribe-to-forward-reference-row)
  - [Subscribe to forward reference row and resource modified](#subscribe-to-forward-reference-row-and-resource-modified)
  - [Subscribe to forward reference row and resource deleted](#subscribe-to-forward-reference-row-and-resource-deleted)
  - [Subscribe to backward reference row](#subscribe-to-backward-reference-row)
  - [Subscribe to backward reference row and resource modified](#subscribe-to-backward-reference-row-and-resource-modified)
  - [Subscribe to backward reference row and resource deleted](#subscribe-to-backward-reference-row-and-resource-deleted)
  - [Subscribe to top-level row](#subscribe-to-top-level-row)
  - [Subscribe to top-level row and resource modified](#subscribe-to-top-level-row-and-resource-modified)
  - [Subscribe to top-level row and resource deleted](#subscribe-to-top-level-row-and-resource-deleted)
  - [Subscribe to forward reference collection](#subscribe-to-forward-reference-collection)
  - [Subscribe to forward reference collection and resource added](#subscribe-to-forward-reference-collection-and-resource-added)
  - [Subscribe to forward reference collection and resource deleted](#subscribe-to-forward-reference-collection-and-resource-deleted)
  - [Subscribe to backward reference collection](#subscribe-to-backward-reference-collection)
  - [Subscribe to backward reference collection and resource added](#subscribe-to-backward-reference-collection-and-resource-added)
  - [Subscribe to backward reference collection and resource deleted](#subscribe-to-backward-reference-collection-and-resource-deleted)
  - [Subscribe to top-level collection](#subscribe-to-top-level-collection)
  - [Subscribe to top-level collection and resource added](#subscribe-to-top-level-collection-and-resource-added)
  - [Subscribe to top-level collection and resource deleted](#subscribe-to-top-level-collection-and-resource-deleted)
  - [Notification to multiple subscribers](#notification-to-multiple-subscribers)
  - [Subscribe to an invalid resource](#subscribe-to-an-invalid-resource)
  - [Duplicate subscription](#duplicate-subscription)
  - [Subscribe to multiple resources and modified](#subscribe-to-multiple-resources-and-modified)
- [REST Selector validation](#rest-selector-validation)

## REST full declarative configuration
### Objective
The objective of the test case is to verify if the user configuration is set in the OVSDB.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
+---------------+                 +---------------+
|               |                 |    Ubuntu     |
|  OpenSwitch   |eth0---------eth1|               |
|               |      lnk01      |  Workstation  |
+---------------+                 +---------------+
```

### Description
This test case verifies if the configuration was set correctly by comparing user configuration (input) with the output of OVSDB read.

 1. Connect OpenSwitch to the Ubuntu workstation as shown in the topology diagram.
 2. Configure the IPV4 address on the switch management interfaces.
 3. Configure the IPV4 address on the Ubuntu workstation.
 4. This script validates if the input configuration is updated correctly in the OVSDB by comparing output configuration (read from OVSDB after write) with user input configuration.

### Test result criteria
#### Test pass criteria
The test case passes if the input configuration matches the output configuration (read from OVSDB after write).

#### Test fail criteria
The test case is failing if the input configuration does not match the output configuration (read from OVSDB after write).

# Notifications test cases
## Add invalid WebSocket subscriber through REST
### Objective
The objective of the test case is to verify adding of a WebSocket subscriber through REST returns an error.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies a WebSocket based subscriber cannot be created through REST POST. WebSocket subscribers are created only when a client connects via WebSocket.

 1. Attempt to create a subscriber with `type` set to `ws`, in the configuration, and sending a POST request to the `/rest/v1/system/notification_subscribers` path:
    ```
    {
        "configuration": {
            "name": "test_subscriber",
            "type": "ws"
        }
    }
    ```

 2. Verify the HTTP status code in the response is `400`.
 3. Verify the custom validation error code `10005` is in the response data.

### Test result criteria
#### Test pass criteria
The test case is considered passing if the request to create a WebSocket subscriber results in a `400` status code.

#### Test fail criteria
The test case is considered failing if the request to create a WebSocket subscriber through REST is successful and results in a `201` status code.



## Invalid deletion of WebSocket subscriber through REST
### Objective
The objective of the test case is to verify deleting of a WebSocket subscriber through REST returns an error.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies a WebSocket based subscriber cannot be deleted through REST. WebSocket subscribers can only be deleted when the WebSocket disconnected.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Attempt to delete the WebSocket through REST.
 3. Verify the delete request results in a `400` status code.

### Test result criteria
#### Test pass criteria
The test case is considered passing if the request to delete a WebSocket subscriber results in a `400` status code.

#### Test fail criteria
The test case is considered failing if the request to delete a WebSocket subscriber through REST is successful and results in a status code other than `400`.



## WebSocket connect and subscriber created
### Objective
The objective of the test case is to verify establishing a WebSocket connection creates a new subscriber in the database.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that a subscriber is created in the database when a WebSocket connection is established.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.

### Test result criteria
#### Test pass criteria
The test case is considered passing if the `name` of the new subscriber is found in the list of subscribers retrieved from the database.

#### Test fail criteria
The test case is considered failing if the `name` of the new subscriber is not found in the list of subscribers retrieved from the database.



## WebSocket disconnect cleans subscriber data
### Objective
The objective of the test case is to verify that disconnecting a WebSocket cleans the subscriber's data.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that the subscriber's data is cleaned in the database when a WebSocket connection is disconnected.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Close the WebSocket connection.
 5. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 6. Verify the new subscriber identified by its `name` is not found in the list of subscribers.

### Test result criteria
#### Test pass criteria
The test case is considered passing if the `name` of the new subscriber is not found in the list of subscribers retrieved from the database after the WebSocket is closed.

#### Test fail criteria
The test case is considered failing if the `name` of the new subscriber is found in the list of subscribers retrieved from the database after the WebSocket is closed.



## WebSocket disconnect cleans subscription data
### Objective
The objective of the test case is to verify that disconnecting a WebSocket cleans the subscriber's data.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that the subscriber's subscription data is cleaned in the database when a WebSocket connection is disconnected.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Close the WebSocket connection.
 7. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 8. Verify the new subscriber identified by its `name` is not found in the list of subscribers.
 9. Get a list of subscribers, by `resource`, in the database by issuing the `ovsdb-client dump Notification_Subscriptions resource` command on the switch.
 10. Verify the subscription created for the subscriber is not found in the list of subscriptions.

### Test result criteria
#### Test pass criteria
The test case is considered passing if the new subscription is not found in the list of subscriptions retrieved from the database after the WebSocket is closed.

#### Test fail criteria
The test case is considered failing if the new subscription is found in the list of subscriptions retrieved from the database after the WebSocket is closed.



## Subscribe to forward reference row
### Objective
The objective of the test case is to verify that subscribing to a forward reference row notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a forward reference row notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to forward reference row and resource modified
### Objective
The objective of the test case is to verify that modifying a monitored forward reference row notifies the client of the updated resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that modifying a monitored forward reference row notifies the client of the updated values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Modify the resource to trigger a notification by sending a PUT request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": false
        }
    }
    ```

 9. Verify the PUT request results in a `200` status code.
 10. Retrieve and verify the notification message contains the `notifications`, `modified`, and `values` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Verify the updated values from the notification matches the values from the update data.
 13. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 14. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if modifying a monitored resource triggers a notification with the updated values.

#### Test fail criteria
The test case is considered failing if modifying a monitored resource does not trigger a notification or if the updated values do not match with the update data used to modify the resource.



## Subscribe to forward reference row and resource deleted
### Objective
The objective of the test case is to verify that deleting a monitored forward reference row notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a monitored forward reference row notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 9. Verify the DELETE request results in a `204` status code.
 10. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a monitored resource triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a monitored resource does not trigger a notification.



## Subscribe to backward reference row
### Objective
The objective of the test case is to verify that subscribing to a backward reference row notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a backward reference row notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 8. Verify the notification message contains the correct `resource` and `subscription` URIs.
 9. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 10. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 11. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to backward reference row and resource modified
### Objective
The objective of the test case is to verify that modifying a monitored backward reference row notifies the client of the updated resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that modifying a monitored backward reference row notifies the client of the updated values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Modify the resource to trigger a notification by adding a child to the row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.2
    end
    ```

 8. Retrieve and verify the notification message contains the `notifications`, `modified`, and `values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the updated values from the notification matches the values from the update data.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if modifying a monitored resource triggers a notification with the updated values.

#### Test fail criteria
The test case is considered failing if modifying a monitored resource does not trigger a notification or if the updated values do not match with the update data used to modify the resource.



## Subscribe to backward reference row and resource deleted
### Objective
The objective of the test case is to verify that deleting a backward forward reference row notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a monitored backward reference row notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 8. Verify the DELETE request results in a `204` status code.
 9. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 10. Verify the notification message contains the correct `resource` and `subscription` URIs.
 11. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a monitored resource triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a monitored resource does not trigger a notification.



## Subscribe to top-level row
### Objective
The objective of the test case is to verify that subscribing to a top-level row notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a top-level row notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_row_sub",
            "resource": "/rest/v1/system/ports/Port1"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/ports/Port1` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to top-level row and resource modified
### Objective
The objective of the test case is to verify that modifying a monitored top-level row notifies the client of the updated resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that modifying a monitored top-level row notifies the client of the updated values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_row_sub",
            "resource": "/rest/v1/system/ports/Port1"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Modify the resource to trigger a notification by sending a PUT request to the `/rest/v1/system/ports/Port1` URI with the following data:
    ```
    {
        "configuration": {
            "external_ids": {
                "test_key": "test_value"
            }
        }
    }
    ```

 9. Verify the PUT request results in a `200` status code.
 10. Retrieve and verify the notification message contains the `notifications`, `modified`, and `values` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Verify the updated values from the notification matches the values from the update data.
 13. Clean the added resource by sending a DELETE request to the `/rest/v1/system/ports/Port1` URI.
 14. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if modifying a monitored resource triggers a notification with the updated values.

#### Test fail criteria
The test case is considered failing if modifying a monitored resource does not trigger a notification or if the updated values do not match with the update data used to modify the resource.



## Subscribe to top-level row and resource deleted
### Objective
The objective of the test case is to verify that deleting a monitored top-level row notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a monitored top-level row notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_row_sub",
            "resource": "/rest/v1/system/ports/Port1"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/ports/Port1` URI.
 9. Verify the DELETE request results in a `204` status code.
 10. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a monitored resource triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a monitored resource does not trigger a notification.



## Subscribe to forward reference collection
### Objective
The objective of the test case is to verify that subscribing to a forward reference collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a forward reference collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to forward reference collection and resource added
### Objective
The objective of the test case is to verify that adding a resource to a monitored forward reference collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that adding a resource to a monitored forward reference collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new forward reference row, to trigger an added notification, by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if adding a resource to a monitored collection triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if adding a resource to a monitored collection does not trigger a notification or if the initial values do not match the values from the GET request.



## Subscribe to forward reference collection and resource deleted
### Objective
The objective of the test case is to verify that deleting a resource from a monitored forward reference collection notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a resource from a monitored forward reference collection notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 9. Verify the DELETE request results in a `204` status code.
 10. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a resource from a monitored collection triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a resource from a monitored collection does not trigger a notification.



## Subscribe to backward reference collection
### Objective
The objective of the test case is to verify that subscribing to a backward reference collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a backward reference collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 8. Verify the notification message contains the correct `resource` and `subscription` URIs.
 9. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 10. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 11. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to backward reference collection and resource added
### Objective
The objective of the test case is to verify that adding a resource to a monitored backward reference collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that adding a resource to a monitored backward reference collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 8. Verify the notification message contains the correct `resource` and `subscription` URIs.
 9. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 10. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 11. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if adding a resource to a monitored collection triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if adding a resource to a monitored collection does not trigger a notification or if the initial values do not match the values from the GET request.



## Subscribe to backward reference collection and resource deleted
### Objective
The objective of the test case is to verify that deleting a resource from a monitored backward reference collection notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a resource from a monitored backward reference collection notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new backward reference row by issuing the following commands on the switch:
    ```
    configure terminal
    ip route 10.0.0.0/8 10.0.0.1
    end
    ```

 5. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "back_ref_coll_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/routes"
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/routes/static/10.0.0.0%2F8` URI.
 8. Verify the DELETE request results in a `204` status code.
 9. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 10. Verify the notification message contains the correct `resource` and `subscription` URIs.
 11. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a resource from a monitored collection triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a resource from a monitored collection does not trigger a notification.



## Subscribe to top-level collection
### Objective
The objective of the test case is to verify that subscribing to a top-level collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that subscribing to a top-level collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_coll_sub",
            "resource": "/rest/v1/system/ports"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/ports/Port1` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if subscribing does not trigger a notification or if the initial values do not match with the values retrieved from the GET request.



## Subscribe to top-level collection and resource added
### Objective
The objective of the test case is to verify that adding a resource to a monitored top-level collection notifies the client of the initial resource values.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that adding a resource to a monitored top-level collection notifies the client of the initial values. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_coll_sub",
            "resource": "/rest/v1/system/ports"
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Retrieve and verify the notification message contains the `notifications`, `added`, and `new_values` fields.
 9. Verify the notification message contains the correct `resource` and `subscription` URIs.
 10. Verify the initial values from the notification matches the values retrieved from the GET request for the resource.
 11. Clean the added resource by sending a DELETE request to the `/rest/v1/system/vrfs/ports/Port1` URI.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if adding a resource to a monitored collection triggers a notification with the initial values.

#### Test fail criteria
The test case is considered failing if adding a resource to a monitored collection does not trigger a notification or if the initial values do not match the values from the GET request.



## Subscribe to top-level collection and resource deleted
### Objective
The objective of the test case is to verify that deleting a resource from a monitored top-level collection notifies the client.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that deleting a resource from a monitored top-level collection notifies the client. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new top-level row by sending a POST request to the `/rest/v1/system/ports` URI with the following data:
    ```
    {
        "configuration": {
            "name": "Port1",
            "interfaces": ["/rest/v1/system/interfaces/1"],
            "trunks": [413],
            "ip4_address_secondary": ["192.168.1.1"],
            "lacp": "active",
            "bond_mode": "l2-src-dst-hash",
            "tag": 654,
            "vlan_mode": "trunk",
            "ip6_address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "external_ids": {"extid1key": "extid1value"},
            "mac": "01:23:45:67:89:ab",
            "other_config": {"cfg-1key": "cfg1val"},
            "bond_active_slave": "null",
            "ip6_address_secondary": ["01:23:45:67:89:ab"],
            "ip4_address": "192.168.0.1",
            "admin": "up",
            "ospf_auth_text_key": "null",
            "ospf_auth_type": "null",
            "ospf_if_out_cost": 10,
            "ospf_if_type": "ospf_iftype_broadcast",
            "ospf_intervals": {"transmit_delay": 1},
            "ospf_mtu_ignore": false,
            "ospf_priority": 0,
        },
        "referenced_by": [{"uri": "/rest/v1/system/bridges/bridge_normal"}]
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "top_level_coll_sub",
            "resource": "/rest/v1/system/ports"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/ports/Port1` URI.
 9. Verify the DELETE request results in a `204` status code.
 10. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 11. Verify the notification message contains the correct `resource` and `subscription` URIs.
 12. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a resource from a monitored collection triggers a notification.

#### Test fail criteria
The test case is considered failing if deleting a resource from a monitored collection does not trigger a notification.



## Notification to multiple subscribers
### Objective
The objective of the test case is to verify that multiple subscribers can receive notifications for the same monitored resource.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description
This test case verifies that notifications for a monitored resource can be sent to multiple subscribers. This test case also validates the format of the notification message.

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI to establish a connection for the first subscriber.
 2. Connect to the switch, using WebSockets, at the same URI to establish a connection for the second subscriber.
 3. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 4. Verify the new subscribers identified by their `name` exists in the list of subscribers.
 5. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 6. Verify the POST request results in a `201` status code.
 7. Create a new subscription for the first subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER1_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 8. Verify the POST request results in a `201` status code.
 9. Create a new subscription for the second subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER2_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 10. Verify the POST request results in a `201` status code.
 11. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 12. Verify the DELETE request results in a `204` status code.
 13. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 14. Verify the notification message contains the correct `resource` and `subscription` URIs for both subscribers.
 15. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a monitored resource triggers notifications for both subscribers.

#### Test fail criteria
The test case is considered failing if deleting a monitored resource does not trigger a notification on either subscribers.



## Subscribe to an invalid resource
### Objective
The objective of the test case is to verify that subscribing to an invalid resource will result in an unsuccessful response.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 5. Verify the POST request results in a `400` status code because the resource does not exist.
 6. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if subscribing to an invalid resource results in a `400` status code in the response.

#### Test fail criteria
The test case is considered failing if subscribing to an invalid resource results in a `201` status code in the response.



## Duplicate subscription
### Objective
The objective of the test case is to verify that subscribing to a resource that has already been subscribed to will result in an unsuccessful response.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create another subscription for the subscriber and subscribe to the same resource with the following data:
    ```
    {
        "configuration": {
            "name": "duplicate_subscription",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers"
        }
    }
    ```

 7. Verify the POST request results in a `400` status code because the resource is already subscribed to in another subscription.
 8. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if creating a duplicate subscription results in a `400` status code in the response.

#### Test fail criteria
The test case is considered failing if creating a duplicate subscription results in a `201` status code in the response.



## Subscribe to multiple resources and modified
### Objective
The objective of the test case is to verify notifications for multiple resources for the same subscriber.

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram

```ditaa
    +------------------+              +------------+
    |                  |              |            |
    |    OpenSwitch    |--------------|    Host    |
    |                  |              |            |
    +------------------+              +------------+
```

### Description

 1. Connect to the switch, using WebSockets, at the `wss://SWITCH_IP/rest/v1/ws/notifications` URI.
 2. Get a list of subscribers, by name, in the database by issuing the `ovsdb-client dump Notification_Subscriber name` command on the switch.
 3. Verify the new subscriber identified by its `name` exists in the list of subscribers.
 4. Create a new forward reference row by sending a POST request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers` URI with the following data:
    ```
    {
        "configuration": {
            "always_compare_med": true,
            "asn": 6001
        }
    }
    ```

 5. Verify the POST request results in a `201` status code.
 6. Create a new subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_sub",
            "resource": "/rest/v1/system/vrfs/vrf_default/bgp_routers/6001"
        }
    }
    ```

 7. Verify the POST request results in a `201` status code.
 8. Create a another subscription for the subscriber by sending a POST request to the `/rest/v1/system/notification_subscribers/SUBSCRIBER_NAME/notification_subscriptions` URI with the following data:
    ```
    {
        "configuration": {
            "name": "forward_ref_row_parent",
            "resource": "/rest/v1/system/vrfs/vrf_default"
        }
    }
    ```

 9. Verify the POST request results in a `201` status code.
 10. Delete the added resource to trigger a notification by sending a DELETE request to the `/rest/v1/system/vrfs/vrf_default/bgp_routers/6001` URI.
 11. Verify the DELETE request results in a `204` status code.
 12. Retrieve and verify the notification message contains the `notifications` and `deleted` fields.
 13. Verify the notification message contains the correct `resource` and `subscription` URIs for both subscriptions.
 14. Close the WebSocket connection.

### Test result criteria
#### Test pass criteria
The test case is considered passing if deleting a monitored resource triggers a notification for both subscriptions.

#### Test fail criteria
The test case is considered failing if deleting a monitored resource does not trigger a notification for either subscriptions.

## REST Selector validation

### Objective
The objective of the test case is to verify the *selector* query argument

### Requirements
The requirements for this test case are:

- OpenSwitch
- Ubuntu Workstation

### Setup
#### Topology diagram
```ditaa
+---------------+                 +---------------+
|               |                 |    Ubuntu     |
|  OpenSwitch   |eth0---------eth1|               |
|               |      lnk01      |  Workstation  |
+---------------+                 +---------------+
```

### Description
This test case validates the *selector* query parameter through the standard REST API GET method.

1. Verify if response has a `400 BAD REQUEST` HTTP response status code by using a invalid selector
   parameter in combination with the *depth* parameter.
    a. Execute the GET request over `/rest/v1/system/interfaces?selector=invalid;depth=1`
    b. Verify if the HTTP response is `400 BAD REQUEST`.

2. Verify if response has a `200 OK` HTTP response status code by using a *configuration* selector
   parameter in combination with the *depth* parameter.
    a. Execute the GET request over `/rest/v1/system/interfaces?selector=configuration;depth=1`
    b. Verify if the HTTP response is `200 OK`.

3. Verify if response has a `200 OK` HTTP response status code by using a *status* selector
   parameter in combination with the *depth* parameter.
    a. Execute the GET request over `/rest/v1/system/interfaces?selector=status;depth=1`
    b. Verify if the HTTP response is `200 OK`.

4. Verify if response has a `200 OK` HTTP response status code by using a *statistics* selector
   parameter in combination with the *depth* parameter.
    a. Execute the GET request over `/rest/v1/system/interfaces?selector=statistics;depth=1`
    b. Verify if the HTTP response is `200 OK`.

### Test result criteria
#### Test pass criteria

This test passes by meeting the following criteria:

- Querying a interface list with an invalid *selector* parameter returns a `400 BAD REQUEST`
- Querying a interface list with an valid *selector* parameter returns a `200 OK`

#### Test fail criteria

This test fails when:

- Querying a interface list with an invalid *selector* parameter returns anything other than
  `400 BAD REQUEST` HTTP response
- Querying a interface list with an valid *selector* parameter returns anything other than
  `200 OK` HTTP response
