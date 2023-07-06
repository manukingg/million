import base64
name = 'friend'
source = base64.b64encode(name.encode('utf-8'))
print (source.decode('utf-8'))
backsource = base64.b64decode(source.decode('utf-8')).decode('utf-8')
print (backsource)
