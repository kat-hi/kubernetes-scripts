import subprocess
import pymongo
import time
import json
import os
import sys
import requests

subprocess.run('kubectl apply -f resources/pvc1.yaml -n testing', shell=True)
subprocess.run('kubectl apply -f resources/pvc2.yml -n testing', shell=True)
subprocess.run('kubectl apply -f resources/deployment.yaml -n testing', shell=True)


responsestatus = 500
while responsestatus != 200:
    time.sleep(5.0)
    response = requests.get('https://mongosynctest.app.datexis.com/')
    responsestatus = response.status_code

with open('moredata.json', 'r') as moredata:
    moredata = json.load(moredata)

with open('json.json', 'r') as jsonfile:
    jsondata = json.load(jsonfile)

with open('testdata.json', 'r') as testdata:
    testdata = json.load(testdata)

response = requests.post('https://mongosynctest.app.datexis.com/upload', data=json.dumps(testdata))
print(response.status_code)
response1 = requests.post('https://mongosynctest.app.datexis.com/upload1', data=json.dumps(moredata))
print(response1.status_code)
response2 = requests.post('https://mongosynctest.app.datexis.com/upload2', data=json.dumps(jsondata))
print(response2.status_code)
