import socketio
import requests
from flask import Flask, request, Response
import json
import os
# For dummy results
from minio import Minio
import time
import io

ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", 5000))

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_PORT", 9000))
MINIO_USER = os.getenv("MINIO_USER", "diastema")
MINIO_PASS = os.getenv("MINIO_PASS", "diastema")

# MinIO HOST and Client
minio_host = MINIO_HOST+":"+str(MINIO_PORT)
minio_client = Minio(
        minio_host,
        access_key=MINIO_USER,
        secret_key=MINIO_PASS,
        secure=False
    )

sio = socketio.Server(cors_allowed_origins='*')
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

""" Flask endpoints - Dummy Front End Endpoints """
# A dummy endpoint to represent the answer of the front end services
@app.route("/messages", methods=["POST"])
def modelling():
    message = request.form["message"]
    if(message == "update"):
        print(request.form["message"])
        print(request.form["update"])
    elif(message == "visualize"):
        print(request.form["message"])
        #print(request.form["path"])
        #print(request.form["job"])
        #print(request.form["column"])
    return Response(status=200, mimetype='application/json')

""" Socket IO endpoints - Dummy Diastema Services events """
# A dummy event to represent the answer of the data loading Service
@sio.on("data-loading")
def data_loading(sid, data):
    load_json = data
    job_id = load_json["job-id"]
    #print(load_json)
    
    # Dummy import in Minio
    time.sleep(10)
    json_attrs = load_json
    minio_path  = json_attrs["minio-output"].split("/")
    minio_bucket = minio_path[0]
    del minio_path[0]
    minio_object = '/'.join([str(elem) for elem in minio_path])
    minio_results_object = minio_object + "/loaded.txt"
    minio_client.put_object(minio_bucket, minio_results_object, io.BytesIO(b"results"), 7)
    print("Loading is done")
    
    sioC = socketio.Client()
    sioC.connect("http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT))
    data_to_back = {"loaded":[],"metadata":{},"job-id":job_id}
    sioC.emit("data-loading-done", data_to_back) # Tell orchestrator that loading is done
    sioC.disconnect()
    return 

# A dummy event to represent the answer of the data cleaning Service
@sio.on("data-cleaning")
def data_cleaning(sid, data):
    clean_json = data
    job_id = clean_json["job-id"]
    #print(clean_json)
    
    # Dummy import in Minio
    time.sleep(10)
    json_attrs = clean_json
    minio_path  = json_attrs["minio-output"].split("/")
    minio_bucket = minio_path[0]
    del minio_path[0]
    minio_object = '/'.join([str(elem) for elem in minio_path])
    minio_results_object = minio_object + "/cleaned.txt"
    minio_client.put_object(minio_bucket, minio_results_object, io.BytesIO(b"results"), 7)
    print("Cleaning is done")
    
    sioC = socketio.Client()
    sioC.connect("http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT))
    data_to_back = {"job-id":job_id}
    sioC.emit("data-cleaning-done", data_to_back) # Tell orchestrator that cleaning is done
    sioC.disconnect()
    return 

if __name__ == "__main__":
    app.run("localhost", 5000, True)
