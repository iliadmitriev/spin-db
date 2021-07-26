from os import environ as env
import os
import requests
import socket
import sys
import subprocess
import shutil
import signal

# TODO: remove myself from a list of members in case of crush

timeout = 10


def preexec_function():
    os.setpgrp()
    # signal.signal(signal.SIGINT, signal.SIG_IGN)


def interrupt_handler(signum, frame):
    print("Press ctrl+C")

    if member_id:
        print(f"Removing member {INSTANCE_ID} {INSTANCE_IP} {member_id} from cluster")
        # curl http://10.0.0.10:2379/v2/members/272e204152 -XDELETE
        res = requests.delete(
            url=CLIENT_REQUEST_URL + f'/{member_id}',
            timeout=timeout
        )
        if res.status_code == 204:
            print(f"Removed member {INSTANCE_ID}")
        else:
            print(res.request.url, res.request.headers, res.request.body)
            print(res, res.text)
    else:
        exit()


signal.signal(signal.SIGINT, interrupt_handler)

member_id = None

SECRET_TOKEN = env.get('SECRET_TOKEN', 'test_token')

CLIENT_PORT = env.get('CLIENT_PORT', 2379)
SERVER_PORT = env.get('SERVER_PORT', 2380)

INSTANCE_ID = env.get('POD_NAME', socket.gethostname())
INSTANCE_IP = env.get('POD_IP', '127.0.0.1')

DATA_DIR = env.get('DATA_DIR', f"data/{INSTANCE_ID}")

CLIENT_SCHEME = env.get('CLIENT_SCHEME', 'http')
PEER_SCHEME = env.get('PEER_SCHEME', 'http')

CLIENT_REQUEST_HOST = env.get('CLIENT_REQUEST_HOST', '127.0.0.1')

CLIENT_REQUEST_URL = f"{CLIENT_SCHEME}://{CLIENT_REQUEST_HOST}:{CLIENT_PORT}/v2/members"

cluster_found = False

try:
    peer_urls_response = requests.get(url=CLIENT_REQUEST_URL, timeout=timeout)
    response = peer_urls_response.json()
    cluster_found = True
except requests.exceptions.ConnectionError:
    response = None

if not cluster_found:
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

    command = [
        "etcd",
        "--data-dir", DATA_DIR,
        "--enable-v2",
        "--name", f"{INSTANCE_ID}",
        "--listen-client-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{CLIENT_PORT}",
        "--advertise-client-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{CLIENT_PORT}",
        "--listen-peer-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}",
        "--initial-advertise-peer-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}",
        "--initial-cluster-token", f"{SECRET_TOKEN}",
        "--initial-cluster-state", "new"
    ]
    subprocess.call(command, stdout=sys.stdout, preexec_fn=preexec_function)

else:

    initial_cluster = []

    for member in response.get('members'):
        if member.get('name') and member.get('peerURLs') \
                and len(member.get('peerURLs')):
            name = member.get('name')
            peer_url_first = member.get('peerURLs').pop()
            initial_cluster.append(f'{name}={peer_url_first}')

    initial_cluster.append(f'{INSTANCE_ID}={CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}')

    print(f"initial_cluster={initial_cluster}")

    client_url = CLIENT_REQUEST_URL

    # TODO: find and remove my previous instance from cluster

    # create entering cluster request
    add_response = requests.post(
        url=client_url,
        json={
            'peerURLs': [
                f"{CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}"
            ],
            'name': INSTANCE_ID
        },
        timeout=timeout
    )

    if add_response.status_code != 201:
        print("Error")
        print(add_response.status_code)
        print(add_response.text)
    else:
        member_id = add_response.json().get('id')
        print('member_id=', member_id)

    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

    command = [
        "etcd",
        "--data-dir", DATA_DIR,
        "--enable-v2",
        "--name", f"{INSTANCE_ID}",
        f"--initial-cluster", ','.join(initial_cluster),
        "--listen-client-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{CLIENT_PORT}",
        "--advertise-client-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{CLIENT_PORT}",
        "--listen-peer-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}",
        "--initial-advertise-peer-urls", f"{CLIENT_SCHEME}://{INSTANCE_IP}:{SERVER_PORT}",
        "--initial-cluster-token", f"{SECRET_TOKEN}",
        "--initial-cluster-state", "existing"
    ]
    subprocess.call(command, stdout=sys.stdout, preexec_fn=preexec_function)
