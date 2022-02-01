import socketio
import json
from flask import Flask
from minio import Minio
from pymongo import MongoClient
import requests
import os

sio = socketio.Client()

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_PORT", 9000))
MINIO_USER = os.getenv("MINIO_USER", "diastema")
MINIO_PASS = os.getenv("MINIO_PASS", "diastema")

ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", 5000))

# MinIO HOST and Client
minio_host = MINIO_HOST+":"+str(MINIO_PORT)
minio_client = Minio(
        minio_host,
        access_key=MINIO_USER,
        secret_key=MINIO_PASS,
        secure=False
    )

# insert data into MinIO
raw_bucket_minIO = "bio/analysis-a22afdb473bcd/raw"

if minio_client.bucket_exists("bio") == False:
        minio_client.make_bucket("bio")

minio_client.fput_object(
    "bio", "analysis-a22afdb473bcd/raw/test_analysis1.txt", "test_analysis1.txt"
)
minio_client.fput_object(
    "bio", "analysis-a22afdb473bcd/raw/test_analysis2.txt", "test_analysis2.txt"
)

playbook = {
  "diastema-token": "diastema-key",
  "analysis-id": "a22afdb473bcd",
  "database-id": "BIO",
  "analysis-datetime": "2021-10-06 02:55:45:796",
  "jobs": [
    {
      "id": 1633477964372,
      "step": 1,
      "from": 0,
      "next": [
        2
      ],
      "title": "data-load",
      "save": False,
      "files": raw_bucket_minIO,
      "dataset-name": "ships"
    },
    {
      "id": 1633478113563,
      "step": 2,
      "from": 1,
      "next": [
        3
      ],
      "title": "cleaning",
      "save": False,
      "max-shrink": 0.56
    },
    {
      "id": 1633478115115,
      "step": 3,
      "from": 2,
      "next": [
        4
      ],
      "title": "classification",
      "save": False,
      "algorithm": "logistic regression",
      "column": "ID"
    },
    {
      "id": 1633478116819,
      "step": 4,
      "from": 3,
      "next": [
        0
      ],
      "title": "visualize",
      "save": False
    }
  ],
  "nodes": [
    {
      "_id": 1633477964372,
      "position": {
        "top": 268,
        "left": 344
      },
      "property": "Data Load",
      "type": "Data Load"
    },
    {
      "_id": 1633478113563,
      "position": {
        "top": 273,
        "left": 604
      },
      "property": "Cleaning",
      "field": "",
      "type": "Cleaning"
    },
    {
      "_id": 1633478115115,
      "position": {
        "top": 376.00000762939453,
        "left": 864
      },
      "property": "Select Algorithm",
      "field": "ID",
      "type": "Classification"
    },
    {
      "_id": 1633478116819,
      "position": {
        "top": 286.00000762939453,
        "left": 1188
      },
      "property": "Visualize",
      "type": "Visualize"
    }
  ],
  "connections": [
    {
      "from": 1633477964372,
      "to": 1633478113563
    },
    {
      "from": 1633478113563,
      "to": 1633478115115
    },
    {
      "from": 1633478115115,
      "to": 1633478116819
    }
  ],
  "metadata":{"attr1":"value1", "attr2":"value2"},
  "automodel": False
}

### System Events
# Connect
@sio.event
def connect():
    print("I'm connected")
    
# Connect Error
@sio.event
def connect_error(data):
    print("Connection failed. Data:\n", data)

# Disconnect
@sio.event
def disconnect():
    print("I'm disconnected")

### Event Handlers -> Routes
@sio.on("speak")
def speak():
    diastema_playbook = json.dumps(playbook)
    sio.emit("analysis", {"analysis": diastema_playbook}) # Send to server

# Catch All -> 404
@sio.on("*")
def catch_all(event, data):
    print("Event doesn't have a registered handler")


if __name__ == "__main__":
    sio.connect("http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT))
    print("Client SID", sio.sid)
    speak()
    sio.disconnect()
