from hcloud import Client
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image
from hcloud.locations.domain import Location
import paramiko

API_TOKEN = 'NOSsbf93NQYRCQsb1kr3CoSLQTXRbvVraoNSJDPjIkdZYdZSZzRUOaTt8Zi4q4BS'
SSH_KEY = 'Main'
SERVER_NAME = 'test-server123'
SERVER_TYPE = 'cx11'
SERVER_IMAGE = 'docker-ce'
SERVER_LOCATION = 'hel1'

def create_server():
    client = Client(token=API_TOKEN)
    ssh_key = client.ssh_keys.get_by_name(name=SSH_KEY)
    response = client.servers.create(
        name=SERVER_NAME,
        server_type=ServerType(name=SERVER_TYPE),
        image=Image(name=SERVER_IMAGE),
        location=Location(name=SERVER_LOCATION),
        ssh_keys=[ssh_key],
        )
    server = response.server
    server_ip = server.public_net.ipv4.ip
    print(f'Server created with this IP: {server_ip}')
    print("Root Password: ", response.root_password)
    print(server)
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh_client.connect(hostname=response.server.public_net.ipv4.ip, username='root')
    stdin, stdout, stderr = ssh_client.exec_command('ls -la')
    print(stdout.read().decode('utf-8'))
    ssh_client.close()

if __name__ == '__main__':
    create_server()