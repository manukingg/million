import time
import http.client
import db as dbu
import docker
import threading
import subprocess
import time
import base64
import random
import secrets
import string
import json
import datetime
from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image
from hcloud.locations.domain import Location
from mixpanel import Mixpanel
import hashlib
import pathlib
import paramiko
import logging
import socks
from docker.transport import SSHHTTPAdapter
from google.cloud import storage

def SSHHTTPAdapter_patched_connect(self):
        if self.ssh_client:
            logging.info(f"Trying to connect to {self.ssh_params['hostname']} through socks5 inside docker client patch.")
            sock = socks.socksocket()
            sock.set_proxy(
                proxy_type=socks.SOCKS5,
                addr="0.0.0.0",
                port=1070,
            )
            sock.connect((self.ssh_params['hostname'], 22))
            logging.info(f"Successfully connected to {self.ssh_params['hostname']} through socks5 inside docker client patch.")
            self.ssh_params['sock'] = sock
            #self.ssh_params['key_filename'] = '/home/shocoladka/.ssh/humanvpn_id_rsa'
            self.ssh_client.connect(**self.ssh_params)
SSHHTTPAdapter._connect = SSHHTTPAdapter_patched_connect

logging.basicConfig(level=logging.INFO)

TRIAL_SERVER_IP = '128.140.34.117'
HETZNER_API_TOKEN = 'NOSsbf93NQYRCQsb1kr3CoSLQTXRbvVraoNSJDPjIkdZYdZSZzRUOaTt8Zi4q4BS'
REG_API_TOKEN = 'cf78246f88c2d68091efc8daaf101764b72513fe4e01b9fbe7906c50b9fc50824211eb24eca67592d80282664ec6a08f'
mp = Mixpanel('ba4f4c87c35eabfbb7820e21724aaa26')
DB_TABLE_NAME = 'users_info_ru'
ALPHABET = string.ascii_letters + string.digits
PAYMENT_KEY = 'y4FWxjLLtiR16WEsiHydXAyQ6PQioKKDwW8ECjMgQa7tj7DulwWfSoyh8gbJmdXtRaCkS6k7QqE8fX1BxJOtUJ4MRoNkPQAWQUKQDCrOmVQwuCBpY5pKvEJO3P6wSomL'
MERCHANT_UUID = '3b89f29b-2459-4bbd-bace-2f2e14df7aed'

def duplicate_server(cursor, server_ip):
    server_id = dbu.fetch_one_for_query(cursor, 'SELECT server_id FROM servers WHERE server_IP = %s', server_ip)
    client = Client(token=HETZNER_API_TOKEN)
    server = client.servers.get_by_id(server_id)
    previous_server_location = server.datacenter.location
    #info about previous server
    SSH_KEY = 'GCP'
    SERVER_LOCATION = previous_server_location
    SERVER_NAME = f'{SERVER_LOCATION}-{int(time.time())}'
    if SERVER_LOCATION == 'ash' or SERVER_LOCATION == 'hil':
        SERVER_TYPE = 'cpx11'
    else:
        SERVER_TYPE = 'cx11'
    SERVER_IMAGE = 'docker-ce'
    #params for new server
    ssh_key = client.ssh_keys.get_by_name(name=SSH_KEY)
    logging.info(f"Creating a duplicate hetzner server for a server with id {server_id} {SERVER_NAME} at {SERVER_LOCATION}.")
    response = client.servers.create(
        name=SERVER_NAME,
        server_type=ServerType(name=SERVER_TYPE),
        image=Image(name=SERVER_IMAGE),
        location=Location(name=SERVER_LOCATION),
        ssh_keys=[ssh_key],
    )
    server = response.server
    new_server_ip = server.public_net.ipv4.ip
    logging.info(f"Hetzner server {SERVER_NAME} created with ip {new_server_ip}, awaiting running.")
    new_server_id = server.id
    #new server created
    #starting loop to create dockers on a new server
    entries = dbu.fetch_all_for_query(cursor, 'SELECT chat_id FROM users_info_ru WHERE server_ip = %s', server_ip)
    for (chat_id,) in entries:
        ensure_ssh_connection(new_server_ip)
        logging.info(f"Creating docker client connection to {new_server_ip}")
        client = docker.DockerClient(
            base_url=f'ssh://root@{new_server_ip}',
        )
        method = 'chacha20-ietf-poly1305'
        password = str(dbu.fetch_one_for_query(cursor, 'SELECT password FROM users_info_ru WHERE chat_id = %s', chat_id))
        server_port = str(dbu.fetch_one_for_query(cursor, 'SELECT port FROM users_info_ru WHERE chat_id = %s', chat_id))
        logging.info(f"Running docker container with {method} {new_server_ip} {server_port}")
        container = client.containers.run(
            'shadowsocks/shadowsocks-libev',
            environment={'PASSWORD': password, 'METHOD': method},
            ports={8388: ('0.0.0.0', server_port), '8388/udp': ('0.0.0.0', server_port)},
            detach=True,
            restart_policy={'Name': 'always'})
        container_id = container.id
        uri = f'{method}:{password}@{new_server_ip}:{server_port}'
        encoded_uri = 'ss://' + base64.b64encode(uri.encode('utf-8')).decode('utf-8')

def get_invoice_json(invoice_id):
    conn = http.client.HTTPSConnection("api.cryptomus.com")
    payload = json.dumps({
        'order_id': invoice_id
    })
    payload_base64 = base64.b64encode(payload.encode('utf-8'))
    data_to_hash = payload_base64 + PAYMENT_KEY.encode('utf-8')
    md5_hash = hashlib.md5(data_to_hash).hexdigest()
    headers = {
        'merchant': MERCHANT_UUID,
        'sign': md5_hash,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/v1/payment/info", payload, headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    json_data = json.loads(data)
    return json_data

def create_server_reg(cursor):
    conn = http.client.HTTPSConnection("api.cloudvps.reg.ru")
    payload = json.dumps({
        'size': 'base-1',
        'image': 3200849,
        'ssh_keys':['cf:87:9a:2e:f1:07:9d:48:a2:fc:de:1c:78:03:50:a8']
    })
    headers = {
        'Authorization': f'Bearer {REG_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    logging.info(f"Creating a reg server.")
    conn.request("POST", "/v1/reglets", payload, headers)
    response = conn.getresponse()
    data = response.read().decode("utf-8")
    json_data = json.loads(data)
    logging.info(f"Response from reg for server creation request: {json_data}")
    server_id = json_data['reglet']['id']
    time.sleep(10)
    while True:
        conn.request("GET", f"/v1/reglets/{server_id}", '', headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        json_data = json.loads(data)
        logging.info(f"Response from reg for server status update request: {json_data}")
        server_status = json_data['reglet']['status']
        logging.info(f"Server status: {server_status}")
        if server_status == 'active':
            break
        time.sleep(5)
    time.sleep(150)
    server_location = json_data['reglet']['region_slug']
    server_ip = json_data['reglet']['ip']
    server_name = json_data['reglet']['name']
    dbu.update(cursor, 'INSERT INTO servers (server_location, server_IP, user_amount, server_name, server_id) VALUES (%s, %s, %s, %s, %s)',
               server_location, server_ip, 0, server_name, server_id)
    cursor._connection.commit()
    return server_ip

def create_server_hetzner(cursor, chat_id):
    SSH_KEY = 'GCP'
    SERVER_LOCATION = dbu.fetch_one_for_query(
        cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
    SERVER_NAME = f'{SERVER_LOCATION}-{int(time.time())}'
    if SERVER_LOCATION == 'ash' or SERVER_LOCATION == 'hil':
        SERVER_TYPE = 'cpx11'
    else:
        SERVER_TYPE = 'cx11'
    SERVER_IMAGE = 'docker-ce'
    client = Client(token=HETZNER_API_TOKEN)
    ssh_key = client.ssh_keys.get_by_name(name=SSH_KEY)
    logging.info(f"Creating a hetzner server {SERVER_NAME} at {SERVER_LOCATION}.")
    response = client.servers.create(
        name=SERVER_NAME,
        server_type=ServerType(name=SERVER_TYPE),
        image=Image(name=SERVER_IMAGE),
        location=Location(name=SERVER_LOCATION),
        ssh_keys=[ssh_key],
    )
    server = response.server
    new_server_ip = server.public_net.ipv4.ip
    logging.info(f"Hetzner server {SERVER_NAME} created with ip {new_server_ip}, awaiting running.")
    new_server_id = server.id
    dbu.update(cursor, 'INSERT INTO servers (server_location, server_IP, user_amount, server_name, server_id) VALUES (%s, %s, %s, %s, %s)',
               SERVER_LOCATION, new_server_ip, 0, SERVER_NAME, new_server_id)
    cursor._connection.commit()
    logging.info(f"Hetzner server {SERVER_NAME} added to DB.")
    while True:
        server = client.servers.get_by_id(server.id)
        if server.status == 'running':
            break
        time.sleep(5)
    time.sleep(15)
    logging.info(f"Hetzner server {SERVER_NAME} running.")
    return new_server_ip

def ensure_ssh_connection(server_ip):
    logging.info(f"Checking ssh connection to {server_ip} running.")
    pathlib.Path(f'{str(pathlib.Path.home())}/.ssh/known_hosts').touch()
    logging.info(f"Establishing sock connection to {server_ip}.")
    sock = socks.socksocket()
    sock.set_proxy(
        proxy_type=socks.SOCKS5,
        addr="0.0.0.0",
        port=1070,
    )
    sock.connect((server_ip, 22))
    logging.info(f"Successfully Established sock connection to {server_ip}.")
    paramiko_client = paramiko.client.SSHClient()
    paramiko_client.load_host_keys(f'{str(pathlib.Path.home())}/.ssh/known_hosts')
    paramiko_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    paramiko_client.connect(server_ip, username='root', sock=sock)#, key_filename='/home/shocoladka/.ssh/humanvpn_id_rsa')
    paramiko_client.save_host_keys(f'{str(pathlib.Path.home())}/.ssh/known_hosts')
    logging.info(f"Ssh connection to {server_ip} successfull.")
   
def create_shadowsocks_server_for_user(cursor, chat_id):
    server_row = dbu.fetch_row_for_query(
        cursor, 'SELECT server_IP FROM servers WHERE server_location = (SELECT server_location FROM users_info_ru WHERE chat_id = %s) AND user_amount < 20 ORDER BY user_amount DESC LIMIT 1', chat_id)
    if server_row is None:
        server_location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
        if server_location == 'msk1':
            server_ip = create_server_reg(cursor)
        else:
            server_ip = create_server_hetzner(cursor, chat_id)
        user_amount = 0
    else:
        server_ip = server_row[0]
        user_amount = dbu.fetch_one_for_query(cursor, 'SELECT user_amount FROM servers WHERE server_ip = %s', server_ip)
        if user_amount == 18:
            server_location = dbu.fetch_one_for_query(cursor, 'SELECT server_location FROM users_info_ru WHERE chat_id = %s', chat_id)
            if server_location == 'msk1':
                create_server_reg(cursor)
            else:
                create_server_hetzner(cursor, chat_id)
    ensure_ssh_connection(server_ip)
    logging.info(f"Creating docker client connection to {server_ip}")
    client = docker.DockerClient(
        base_url=f'ssh://root@{server_ip}',
    )
    method = 'chacha20-ietf-poly1305'
    password = ''.join(secrets.choice(ALPHABET) for i in range(10))
    server_port = str(random.randint(1000, 10000))
    logging.info(f"Running docker container with {method} {server_ip} {server_port}")
    container = client.containers.run(
        'shadowsocks/shadowsocks-libev',
        environment={'PASSWORD': password, 'METHOD': method},
        ports={8388: ('0.0.0.0', server_port), '8388/udp': ('0.0.0.0', server_port)},
        detach=True,
        restart_policy={'Name': 'always'})
    container_id = container.id
    uri = f'{method}:{password}@{server_ip}:{server_port}'
    server_data = {
        "server": f"{server_ip}",
        "server_port": f"{server_port}",
        "password": f"{password}",
        "method": f"{method}" 
    }
    json_server_data = json.dumps(server_data, indent=4)
    google_client = storage.Client(project='humanvpn')
    bucket = google_client.get_bucket('humanvpn-configs')
    blob = bucket.blob(f'{chat_id}')
    blob.upload_from_string(json_server_data, content_type='application/json')
    blob.cache_control = "no-cahe, max-age=0"
    blob.patch()
    json_url = str(blob.public_url)
    user_url = 'ssconf' + json_url[5:]
    #encoded_uri = 'ss://' + base64.b64encode(uri.encode('utf-8')).decode('utf-8')
    user_amount += 1
    dbu.update(cursor, 'UPDATE servers SET user_amount = %s WHERE server_IP = %s', user_amount, server_ip)
    dbu.update(cursor, 'UPDATE users_info_ru SET server_ip = %s, port = %s, password = %s, link = %s, container_id = %s WHERE chat_id = %s',
               server_ip, server_port, password, user_url, container_id, chat_id)
    logging.info(f"Updated db for chat {chat_id} with {server_ip} {server_port} with uri {user_url}")

def get_invoice_status(conn, invoice_id):
    try:
        payload = json.dumps({
            'order_id': invoice_id
        })
        payload_base64 = base64.b64encode(payload.encode('utf-8'))
        data_to_hash = payload_base64 + PAYMENT_KEY.encode('utf-8')
        md5_hash = hashlib.md5(data_to_hash).hexdigest()
        headers = {
            'merchant': MERCHANT_UUID,
            'sign': md5_hash,
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/v1/payment/info", payload, headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        json_data = json.loads(data)
        invoice_status = json_data['result']['payment_status']
        return invoice_status
    except Exception as e:
        logging.error(f'Got error while getting invoice {invoice_id} status: {e}')
        return None

def settle_open_invoices(cursor):
    entries = dbu.fetch_all_for_query(cursor, 'SELECT id, chat_id, duration_days, activated_manually FROM invoices WHERE status = %s', 'check')
    conn = http.client.HTTPSConnection("api.cryptomus.com")
    for invoice_id, chat_id, days, activated_manually in entries:
        if activated_manually == 1 or get_invoice_status(conn, invoice_id) == 'paid':
            mp.track(str(chat_id), 'User purchased VPN', {'Ordered for': f'{days} days'})
            current_expiration_date = dbu.fetch_one_for_query(
                cursor, 'SELECT expiration_date FROM users_info_ru WHERE chat_id = %s', chat_id)
            order_date = datetime.datetime.now()
            if current_expiration_date == None or current_expiration_date < order_date:
                expiration_date = (order_date + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            else:
                expiration_date = (current_expiration_date + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            dbu.update(cursor, 'UPDATE users_info_ru SET expiration_date = %s WHERE chat_id = %s', expiration_date, chat_id)
            dbu.update(cursor, 'UPDATE invoices SET status = %s WHERE id = %s', 'processed', invoice_id)
            
def settle_active_users_without_server(cursor):
    now = datetime.datetime.now()
    entries = dbu.fetch_all_for_query(cursor, 'SELECT chat_id FROM users_info_ru WHERE expiration_date > %s AND server_ip IS NULL', now)
    for (chat_id,) in entries:
        create_shadowsocks_server_for_user(cursor, chat_id)

def settle_users_on_trial(cursor):
    now = datetime.datetime.now()
    entries = dbu.fetch_all_for_query(cursor, 'SELECT chat_id FROM users_info_ru WHERE expiration_date > %s AND server_ip = %s AND container_id IS NULL', now, TRIAL_SERVER_IP)
    for (chat_id,) in entries:
        ensure_ssh_connection(TRIAL_SERVER_IP)
        logging.info(f"Creating docker client connection to {TRIAL_SERVER_IP}")
        client = docker.DockerClient(
            base_url=f'ssh://root@{TRIAL_SERVER_IP}',
        )
        method = 'chacha20-ietf-poly1305'
        password = ''.join(secrets.choice(ALPHABET) for i in range(10))
        server_port = str(random.randint(1000, 10000))
        logging.info(f"Running docker container with {method} {TRIAL_SERVER_IP} {server_port}")
        container = client.containers.run(
            'shadowsocks/shadowsocks-libev',
            environment={'PASSWORD': password, 'METHOD': method},
            ports={8388: ('0.0.0.0', server_port), '8388/udp': ('0.0.0.0', server_port)},
            detach=True,
            restart_policy={'Name': 'always'})
        container_id = container.id
        uri = f'{method}:{password}@{TRIAL_SERVER_IP}:{server_port}'
        encoded_uri = 'ss://' + base64.b64encode(uri.encode('utf-8')).decode('utf-8')
        dbu.update(cursor, 'UPDATE users_info_ru SET server_ip = %s, port = %s, password = %s, link = %s, container_id = %s WHERE chat_id = %s',
                TRIAL_SERVER_IP, server_port, password, encoded_uri, container_id, chat_id)
        logging.info(f"Updated db for chat {chat_id} with {TRIAL_SERVER_IP} {server_port} with uri {encoded_uri}")

def settle_expired_users(cursor):
    now = datetime.datetime.now()
    entries = dbu.fetch_all_for_query(cursor, 'SELECT server_ip, container_id, chat_id FROM users_info_ru WHERE expiration_date < %s AND server_ip IS NOT NULL', now)
    for server_ip, container_id, chat_id in entries:
        ensure_ssh_connection(server_ip)
        client = docker.DockerClient(
            base_url=f'ssh://root@{server_ip}',
        )
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        dbu.update(cursor, 'UPDATE users_info_ru SET server_ip = NULL, port = NULL, link = NULL, password = NULL, container_id = NULL WHERE chat_id = %s', chat_id)
        dbu.update(cursor, 'UPDATE servers SET user_amount = user_amount - 1 WHERE server_ip = %s', server_ip)

def check_for_location(cursor):
    entries = dbu.fetch_all_for_query(cursor, 'SELECT server_ip, server_location FROM users_info_ru WHERE')
    server_ip = dbu.fetch_one_for_query(cursor, 'SELECT server_ip FROM users_info_ru WHERE chat_id = %s', chat_id)
    container_id = dbu.fetch_one_for_query(cursor, 'SELECT container_id FROM users_info_ru WHERE chat_id = %s', chat_id)
    ensure_ssh_connection(server_ip)
    client = docker.DockerClient(
        base_url=f'ssh://root@{server_ip}'
    )
    container = client.containers.get(container_id)
    container.stop()
    container.remove()
    dbu.update(cursor, 'UPDATE users_info_ru SET server_ip = NULL, port = NULL, link = NULL, password = NULL, container_id = NULL, server_location = %s WHERE chat_id = %s', location, chat_id)
    dbu.update(cursor, 'UPDATE servers SET user_amount = user_amount - 1 WHERE server_ip = %s', server_ip)
    #create_shadowsocks_server_for_user(cursor, chat_id)
    

   

def main():
    while True:
        connection = dbu.connection_pool.get_connection()
        try:
            cursor = connection.cursor()
            settle_open_invoices(cursor)
            settle_active_users_without_server(cursor)
            settle_users_on_trial(cursor)
            settle_expired_users(cursor)
        finally:
            connection.commit()
            connection.close()
            time.sleep(10)


if __name__ == '__main__':
    main()
