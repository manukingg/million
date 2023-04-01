import base64
import docker
import random

client = docker.DockerClient(
    base_url=f'ssh://root@65.108.240.138',
    ssh_config={
        'StrictHostKeyChecking': 'no'
    }
    )
client.containers.list()

method = 'chacha20-ietf-poly1305'
password = 'hatbot3401350'
server = '65.108.240.138'
server_port = str(random.randint(1000, 10000))
client.containers.run(
    'shadowsocks/shadowsocks-libev',
    environment={'PASSWORD':password, 'METHOD':method},
    ports={8388:('0.0.0.0', server_port), '8388/udp':('0.0.0.0', server_port)},
    detach=True)
#docker run -e PASSWORD=hatbot3401350 -e METHOD=chacha20-ietf-poly1305 -p 443:8388 -p 443:8388/udp -d shadowsocks/shadowsocks-libev

uri = f'{method}:{password}@{server}:{server_port}'
encoded_uri = base64.b64encode(uri.encode('utf-8')).decode('utf-8')
print('ss://%s' % encoded_uri)