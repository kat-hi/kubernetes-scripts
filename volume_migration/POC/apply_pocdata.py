import subprocess
import pymongo
import time
import json
import os
import sys

subprocess.run('kubectl apply -f resources/mongo1-deployment.yaml -n testing', shell=True)
subprocess.run('kubectl apply -f resources/mongo-pvc.yaml -n testing', shell=True)

time.sleep(10.0)

try:
    client = pymongo.MongoClient("mongodb://cl-svc-243.ris.beuth-hochschule.de:27017/")
    print('db connection established')

except Exception:
    sys.exit(0)

db = client["sync-db"]
mycol = db["syncing"]
mycol2 = db["syncing2"]
mycol3 = db["syncing3"]

path = os.path.join(os.getcwd(), 'testdata.json')
with open(path) as file:
    data = json.load(file)

print('insert data')
mycol.insert_one(data)
mycol2.insert_one(data)
mycol3.insert_one(data)
