import docker

client = docker.DockerClient(base_url='ssh://root@167.235.72.200')
all_containers = client.containers.list(all=True)

for current_container in all_containers:
    if current_container.status == 'running':
        current_container.stop()
    current_container.remove()
    print(current_container)

print('All links have been deleted')