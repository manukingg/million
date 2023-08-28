import json
from flask import jsonify, Flask, Response

app = Flask(__name__)

@app.route('/x.json')
def give_json():
    with open('server.json', 'r') as json_file:
        content = json_file.read()
        # server_json = json.load(json_file)
    return Response(content, 200, {'content-type': 'binary/octet-stream'})