#!/usr/bin/env python3

import etcd
import json
from os import environ as env

ETCD_HOST = env.get('ETCD_ENDPOINT', '127.0.0.1')
ETCD_PORT = env.get('ETCD_PORT', '2379')
ETCD_WATCH_TIMEOUT = 10

client = etcd.Client(host=ETCD_HOST, port=int(ETCD_PORT))
previous_working_nodes = []
new_working_pg_nodes = []

while True:
    try:
        # save previous nodes list
        previous_working_nodes = new_working_pg_nodes
        new_working_pg_nodes = []

        # get new state of nodes
        current_nodes_response = client.get(
            '/service/main/members'
        )
        for node_txt in current_nodes_response.children:
            node = json.loads(node_txt.value)
            if node.get('state') == 'running':
                new_working_pg_nodes.append(node)
        # get nodes array sorted by 'conn_url'
        new_working_pg_nodes.sort(key=lambda x: x.get('conn_url'))

        # if new nodes not equal previous nodes
        # generate new haproxy config and reload
        if previous_working_nodes != new_working_pg_nodes:
            print([(x.get('state'), x.get('conn_url')) for x in new_working_pg_nodes])

        # awaiting for new event or just wait ETCD_WATCH_TIMEOUT seconds
        event = client.watch(
            '/service/main/members',
            timeout=ETCD_WATCH_TIMEOUT,
            recursive=True
        )

    except etcd.EtcdWatchTimedOut:
        pass

    except KeyboardInterrupt:
        print('Interrupted, exiting ...')
        break
