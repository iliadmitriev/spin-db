#!/usr/bin/env python3

import etcd
import json
import re
from jinja2 import Template
from os import environ as env
import socket
import subprocess

MY_NAME = socket.gethostname()


def reload_haproxy(nodes):
    servers = []
    pattern = r'.*://((\d+\.\d+\.\d+\.\d+):(\d+))/.*'
    for n in nodes:
        if n.get('conn_url'):
            match_object = re.search(pattern, n.get('conn_url'))
            if match_object:
                servers.append({
                    'name': match_object.group(1),
                    'host': match_object.group(2),
                    'port': match_object.group(3)
                })
    rendered = Template(open('/etc/haproxy/haproxy.cfg.jinja2').read()).render({
        'servers': servers
    })
    # write haproxy config to file
    with open('/etc/haproxy/haproxy.cfg', 'w') as cfg:
        cfg.write(rendered)
    # finally reload haproxy service
    print(MY_NAME, 'i had reset haproxy')
    print(MY_NAME, 'new servers is = ', servers)
    subprocess.call(['/sbin/sv', 'restart', 'haproxy'])


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
            reload_haproxy(new_working_pg_nodes)

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
