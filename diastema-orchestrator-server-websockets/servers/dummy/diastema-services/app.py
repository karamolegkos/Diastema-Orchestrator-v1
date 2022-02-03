from flask import Flask, request, Response
import json
import os
# For dummy results
from minio import Minio
import time
import io
import random

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

app = Flask(__name__)

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

@app.route("/data-loading", methods=["POST"])
def data_loading():
    json_body = request.json
    print("Loading JSON Given", flush=True)
    print(json.dumps(json_body), flush=True)
    time.sleep(2)

    json_attrs = json_body
    minio_path  = json_attrs["minio-output"].split("/")
    minio_bucket = minio_path[0]
    del minio_path[0]
    minio_object = '/'.join([str(elem) for elem in minio_path])
    minio_results_object = minio_object + "/loaded.txt"
    minio_client.put_object(minio_bucket, minio_results_object, io.BytesIO(b"results"), 7)


    print("Loading Done", flush=True)
    return Response(status=200, mimetype='application/json')

@app.route("/data-cleaning", methods=["POST"])
def data_cleaning():
    json_body = request.json
    print("Cleaning JSON Given", flush=True)
    print(json.dumps(json_body), flush=True)
    time.sleep(2)

    json_attrs = json_body
    minio_path  = json_attrs["minio-output"].split("/")
    minio_bucket = minio_path[0]
    del minio_path[0]
    minio_object = '/'.join([str(elem) for elem in minio_path])
    minio_results_object = minio_object + "/cleaned.txt"
    minio_client.put_object(minio_bucket, minio_results_object, io.BytesIO(b"results"), 7)

    print("Cleaning Done", flush=True)
    return Response(status=200, mimetype='application/json')

@app.route("/data-loading/progress", methods=["GET"])
def data_loading_progress():
    # here we want to get the value of user (i.e. ?user=some-value)
    id = request.args.get('id')
    print("The Loading id is -->"+str(id),flush=True)

    random_number = random.randint(1, 10)
    if(random_number<7):
        return "progress"
    else:
        return "completed"

@app.route("/data-cleaning/progress", methods=["GET"])
def data_cleaning_progress():
    # here we want to get the value of user (i.e. ?user=some-value)
    id = request.args.get('id')
    print("The Cleaning id is -->"+str(id),flush=True)

    random_number = random.randint(1, 10)
    if(random_number<7):
        return "progress"
    else:
        return "completed"

if __name__ == "__main__":
    app.run("localhost", 5001, True)
