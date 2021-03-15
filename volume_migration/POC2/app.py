import json

from flask import Flask, request
import os

app = Flask(__name__)

DEFAULTRESPONSE = 'nothing to show'


@app.route('/', methods=['GET'])
def hello_world():
    return {'json sagt': 'hallo i bims der json'}


@app.route('/upload', methods=['POST'])
def upload():
    data = json.loads(request.data.decode('utf-8'))
    file = 'testdata.json'
    path = '/data/'
    os.makedirs(os.path.dirname(f'{path}{file}'), exist_ok=True)
    with open(f'{path}{file}', 'w') as file:
        file.write(json.dumps(data))
    return 'upload'


@app.route('/upload1', methods=['POST'])
def upload1():
    data = json.loads(request.data.decode('utf-8'))
    file1 = 'moredata.json'
    path = '/path/to/data/'
    os.makedirs(os.path.dirname(f'{path}{file1}'), exist_ok=True)
    with open(f'{path}{file1}', 'w') as file:
        file.write(json.dumps(data))
    return 'upload1'


@app.route('/upload2', methods=['POST'])
def upload2():
    data = json.loads(request.data.decode('utf-8'))
    file2 = 'json.json'
    path = '/path/to/data/'
    os.makedirs(os.path.dirname(f'{path}{file2}'), exist_ok=True)
    with open(f'{path}{file2}', 'w') as file:
        file.write(json.dumps(data))
    return 'upload2'


@app.route('/route1')
def route1():
    try:
        file1 = 'moredata.json'
        file2 = 'json.json'
        path = '/path/to/data/'
        with open(os.path.join(os.getcwd(), f'{path}{file1}'), 'r') as f:
            data = f.read()
            with open(os.path.join(os.getcwd(), f'{path}{file2}'), 'r') as jf:
                jdata = jf.read()
            jsondata = json.loads(data)
            jsondata2 = json.loads(jdata)
            jsondata['secondfile'] = jsondata2
        if not jsondata:
            return DEFAULTRESPONSE
        return jsondata
    except Exception as e:
        print(e)


@app.route('/route2')
def route2():
    try:
        file = 'testdata.json'
        path = '/data/'
        with open(os.path.join(os.getcwd(), f'{path}{file}'), 'r') as f:
            data = f.read()
            jsondata = json.loads(data)
        if not jsondata:
            return DEFAULTRESPONSE
        return jsondata
    except Exception as e:
        print(e)
