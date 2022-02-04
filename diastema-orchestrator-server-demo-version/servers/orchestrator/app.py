import socketio
import json
import os
import io
import requests
import socket
import time
from flask import Flask, request, jsonify, Response
from minio import Minio
from pymongo import MongoClient

# from minio.error import S3Error

# Example of how the analysis is getting saved
#---------------------------------------------
# Metis -- Analysis-1 -- Raw-Files-1
#       |             |- Data-Load-1
#       |             |- Raw-Files-2
#       |             |- Data-Load-2
#       |             |- Analysis-1-1
#       |             |- Analysis-1-2
#       |             |- Analysis-2-1
#       |
#       |- Analysis-2 -- Raw-Files-1
#                     |- Data-Load-1
#                     |- Analysis-1-1
#                     |- Analysis-1-2
#
# BIO   -- Analysis-1 -- Raw-Files-1
#                     |- Data-Load-1
#                     |- Raw-Files-2
#                     |- Data-Load-2
#                     |- Analysis-1-1
#                     |- Analysis-1-2
#                     |- Analysis-1-2-1
#                     |- Analysis-1-2-2
#                     |- Analysis-1-3
#                     |- Analysis-2-1

""" Initiate flask app with WSGI """
sio = socketio.Server()
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

""" Environment Variables """
# Flask app Host and Port
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# MinIO Host, Port and user details
MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_PORT", 9000))
MINIO_USER = os.getenv("MINIO_USER", "diastema")
MINIO_PASS = os.getenv("MINIO_PASS", "diastema")

# MongoDB Host and Port
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))

# Diastema key
DIASTEMA_KEY = os.getenv("DIASTEMA_KEY", "diastema-key")

# Diastema Front End Host and Port
DIASTEMA_FRONTEND_HOST = os.getenv("DIASTEMA_FRONTEND_HOST", "localhost")
DIASTEMA_FRONTEND_PORT = int(os.getenv("DIASTEMA_FRONTEND_PORT", 5001))

# Diastema Analytcs API Host and Port
DIASTEMA_SERVICES_HOST = os.getenv("DIASTEMA_SERVICES_HOST", "localhost")
DIASTEMA_SERVICES_PORT = int(os.getenv("DIASTEMA_SERVICES_PORT", 5001))

# Spark Cluster Details
KUBERNETES_HOST = os.getenv("KUBERNETES_HOST", "localhost")
KUBERNETES_PORT = int(os.getenv("KUBERNETES_PORT", 6006))

""" Global variables """
# Diastema Token
diastema_token = DIASTEMA_KEY

# Kubernetes component connection to call spark jobs
K8S_HEADER = 64
K8S_FORMAT = 'utf-8'
K8S_ADDR = (KUBERNETES_HOST, KUBERNETES_PORT)

# MongoDB HOST
mongo_host = MONGO_HOST+":"+str(MONGO_PORT)
mongo_client = MongoClient("mongodb://"+mongo_host+"/")

# MinIO HOST and Client
minio_host = MINIO_HOST+":"+str(MINIO_PORT)
minio_client = Minio(
        minio_host,
        access_key=MINIO_USER,
        secret_key=MINIO_PASS,
        secure=False
    )

# Diastema Front End url
diastema_front_end_url = "http://"+DIASTEMA_FRONTEND_HOST+":"+str(DIASTEMA_FRONTEND_PORT)+"/messages"

# Diastema Services url
diastema_services_url = "http://"+DIASTEMA_SERVICES_HOST+":"+str(DIASTEMA_SERVICES_PORT)+"/"

""" Frequently used code """
# Make a good MinIO String
def minioString(obj):
    """
    A Function to cast an object to str and then lowercase it.
    This Function is helping to name paths, needed for the analysis in the right way.

    Args:
        - obj (Python Object): An object to turn it into a lowercase String.

    Returns:
        - Lower cased String (String): The lowecased String of the given object.
    """
    return str(obj).lower()

# Insert one record in mongo
def insertMongoRecord(mongo_db_client, mongo_db_analysis_collection, record):
    """
    A Function used to insert records into the Diastema MongoDB Server.

    Args:
        - mongo_db_client (String): A MongoDB Database as the user who wants to make an analysis.
        - mongo_db_analysis_collection (String): A MongoDB Collection as an Analysis of a User.
        - record (JSON): The record to insert in the given collection.

    Returns:
        - Nothing
    """
    mongo_db = mongo_client[mongo_db_client]
    analysis_collection = mongo_db[mongo_db_analysis_collection]
    analysis_collection.insert_one(record)
    return

# Contact Diastema Front-End for the ending of a job
def diastema_call(message, update = -1, visualization_path = -1, job_name = -1, column = -1):
    """
    This function is making an API request to the Diastema central API Server. 
    It will inform it for the end of a job, or the end of the whole analysis.

    Args:
        - visualization_path (String): The path of the MinIO objects to be visualised.
        - job_name (String): A job name, or the "analysis" value.

    Returns:
        - Nothing
    """
    url = diastema_front_end_url
    form_data = {}

    if(message == "update"):
        form_data = {
            "message": "update",
            "update": update
        }
    elif(message == "visualize"):
        form_data = {
            "message": "visualize",
            "path": visualization_path,
            "job": job_name,
            "column": column
        }
    requests.post(url, form_data)
    return

# Function to start the Services of Diastema
def startService(service_name, json_body):
    url = diastema_services_url+service_name
    requests.post(url, json=json_body)
    return

# Function to view the progress of Diastema Services
def waitForService(service_name, job_id):
    url = diastema_services_url+service_name+"/progress?id="+str(job_id)
    responce = requests.get(url)
    while True:
        time.sleep(2)
        if(responce.text == "complete"):
            break
        responce = requests.get(url)
    return

# Function to get the results of a Diastema Service
def getServiceResults(service_name, job_id):
    url = diastema_services_url+service_name+"/"+str(job_id)
    responce = requests.get(url)
    return

""" Functions to call a spark job """
# Function to send message through sockets
def kubernetes_send(msg):
    socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_client.connect(K8S_ADDR)

    message = msg.encode(K8S_FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(K8S_FORMAT)
    send_length += b' ' * (K8S_HEADER - len(send_length))
    socket_client.send(send_length)
    socket_client.send(message)
    socket_client.recv(2048).decode(K8S_FORMAT)
    # print(socket_client.recv(2048).decode(K8S_FORMAT))
    return

# Function assembling the json content needed to run a spark job in kubernetes
def spark_caller(call_args):
    # minikube default host
    master_host = "192.168.49.2"
    # minikube default port
    master_port = "8443"

    # Probably a variable
    app_name = "distema-job"

    # variable
    path = "local://"+call_args[0]

    # variable
    algorithm = call_args[1]

    # variable
    minio_input = call_args[2]

    # variable
    minio_output = call_args[3]

    # variable
    column = call_args[4]

    diaste_kube_json = {
        "master-host" : master_host,
        "master-port" : master_port,
        "app-name" : app_name,
        "minio-host" : MINIO_HOST,
        "minio-port" : str(MINIO_PORT),
        "minio-user" : MINIO_USER,
        "minio-pass" : MINIO_PASS,
        "path" : path,
        "algorithm" : algorithm,
        "minio-input" : minio_input,
        "minio-output" : minio_output,
        "column" : column
    }

    kubernetes_send(json.dumps(diaste_kube_json))
    return

""" Spark Jobs And Diastema API Jobs """
# Data load job
def data_load(playbook, job, data_set_files):
    """
    A function to handle a Data Loading Job from the Diastema JSON playbook.
    It will setup the folders needed for the spark jobs in the MinIO Database.
    Then it will call the Spark Job after configuring the way that the job must be called.
    After the above, it will use the MongoDB to save the path and the whole job in the needed analysis collection.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Loading Job from the Diastema playbook.
        - data_set_files (String): The path of the Data set files.

    Returns:
        - MinIO path (String): The path that the loaded data are saved.
    """
    # Raw bucket = User/analysis-id/job(-id) - ID will be included in later updates
    # raw_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/raw-"+minioString(job["id"])
    raw_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/raw"

    # Bucket to Load Data = User/analysis-id/job-step
    load_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/loaded-"+minioString(job["step"])

    # Make the load Bucket directory
    minio_client.put_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/loaded-"+minioString(job["step"])+"/", io.BytesIO(b""), 0,)

    # Make websocket call for the Data Loading Service
    loading_info = {"minio-input": raw_bucket, "minio-output": load_bucket, "job-id":minioString(job["id"])}

    # Start Loading Service
    startService("data-loading", loading_info)

    # Wait for loading to End
    waitForService("data-loading", job["id"])

    # Insert the raw and loaded data in MongoDB
    raw_job_record = {"minio-path":raw_bucket, "directory-kind":"raw-data", "for-job-step":minioString(job["step"])}
    data_load_job_record = {"minio-path":load_bucket, "directory-kind":"loaded-data", "job-json":job}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), raw_job_record)
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), data_load_job_record)

    # Contact front end for the ending of the job
    # diastema_call(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"]), "data-load")
    diastema_call(message = "update", update = ("Loaded Dataset with ID: "+minioString(job["id"])))

    # Return the bucket that this job made output to
    return load_bucket

# Cleaning job
def cleaning(playbook, job, last_bucket, max_shrink=False, json_schema=False):
    """
    A function to handle a Data Cleaning Job from the Diastema JSON playbook.
    It will setup the folders needed for the spark jobs in the MinIO Database.
    Then it will call the Spark Job after configuring the way that the job must be called.
    After the above, it will use the MongoDB to save the path and the whole job in the needed analysis collection.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Cleaning Job from the Diastema playbook.
        - last_bucket (String): The path that the raw data are saved.
        - max_shrink (float): The maximm shrinking of the data set to be cleaned.
        - json_schema (JSON): A JSON schema for the data cleaning job.

    Returns:
        - MinIO path (String): The path that the cleaned data are saved.
    """
    # Data Bucket = last jobs output bucket
    data_bucket = last_bucket

    # Analysis Bucket = User/analysis-id/job-step
    analysis_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/cleaned-"+minioString(job["step"])

    # Jobs arguments
    #job_args = ["/root/spark-job/cleaning-job.py", data_bucket, analysis_bucket]

    # Optional args
    #if max_shrink != False:
    #    job_args.append('"'+str(max_shrink)+'"')
    #if json_schema != False:
    #    job_args.append('"'+str(json_schema)+'"')

    # Make the MinIO Analysis buckers
    minio_client.put_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/cleaned-"+minioString(job["step"])+"/", io.BytesIO(b""), 0,)

    # Make the websocket call for the Data Cleaning Service
    form_data = {"minio-input": data_bucket, "minio-output": analysis_bucket, "job-id":minioString(job["id"])}
    # Optional attr max-shrink
    if max_shrink != False:
        form_data["max-shrink"] = max_shrink

    # Make websocket call for the Data Loading Service
    cleaning_info = form_data

    # Start Loading Service
    startService("data-cleaning", cleaning_info)

    # Wait for loading to End
    waitForService("data-cleaning", job["id"])

    # Insert the cleaned data in MongoDB
    cleaning_job_record = {"minio-path":analysis_bucket, "directory-kind":"cleaned-data", "job-json":job}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), cleaning_job_record)

    # Contact front end for the ending of the job
    # diastema_call(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"]), "cleaning")
    diastema_call(message = "update", update = "Cleaning executed.")

    # Return the bucket that this job made output to 
    return analysis_bucket

# Classification job
def classification(playbook, job, last_bucket, algorithm=False, tensorfow_algorithm=False):
    """
    A function to handle a Classification Analysis Job from the Diastema JSON playbook.
    It will setup the folders needed for the spark jobs in the MinIO Database.
    Then it will call the Spark Job after configuring the way that the job must be called.
    After the above, it will use the MongoDB to save the path and the whole job in the needed analysis collection.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Classification Job from the Diastema playbook.
        - last_bucket (String): The path that the non analyzed data are saved.
        - algorithm (String): The algorithm to run.
        - tensorfow_algorithm (String): A tensorflow algorithm to run.

    Returns:
        - MinIO path (String): The path that the analyzed data are saved.
    """
    algorithms = {
        "logistic regression" : False,                  # Not imported yet
        "decision tree classifier" : "decisiontree",
        "random forest classifier" : "randomForest",
        "gradient-boosted tree classifier" : False,     # Not imported yet
        "multilayer perceptron classifier" : False,     # Not imported yet
        "linear support vector machine" : False,        # Not imported yet
        "support vector machine" : False                # Not imported yet
    }

    algorithm_to_use = ""
    default_job = "decision tree classifier"
    if algorithm==False:
        algorithm_to_use = algorithms[default_job]
    else:
        if algorithm in algorithms:
            algorithm_to_use = algorithms[algorithm]
            if algorithm_to_use == False:
                algorithm_to_use = algorithms[default_job]
        else:
            algorithm_to_use = algorithms[default_job]
    
    # Path of classification in Diastema docker image
    analysis_path = "/app/src/ClassificationJob.py"

    # Data Bucket = last jobs output bucket
    data_bucket = last_bucket

    # Analysis Bucket = User/analysis-id/job-step
    analysis_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/classified-"+minioString(job["step"])

    # Jobs arguments
    job_args = [analysis_path, algorithm_to_use, data_bucket, analysis_bucket, job["column"]]

    # Make the MinIO Analysis buckers
    minio_client.put_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/classified-"+minioString(job["step"])+"/", io.BytesIO(b""), 0,)

    # Make the Spark call
    spark_caller(job_args)
    
    # Remove the _SUCCESS file from the  spark job results
    minio_client.remove_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/classified-"+minioString(job["step"])+"/_SUCCESS")
    
    # Insert the classified data in MongoDB
    classification_job_record = {"minio-path":analysis_bucket, "directory-kind":"classified-data", "job-json":job}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), classification_job_record)

    # Contact front end for the ending of the job
    # diastema_call(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"]), "classification")
    diastema_call(message = "update", update = "Classification executed.")

    # Return the bucket that this job made output to 
    return analysis_bucket

# Regression job
def regression(playbook, job, last_bucket, algorithm=False, tensorfow_algorithm=False):
    """
    A function to handle a Regression Analysis Job from the Diastema JSON playbook.
    It will setup the folders needed for the spark jobs in the MinIO Database.
    Then it will call the Spark Job after configuring the way that the job must be called.
    After the above, it will use the MongoDB to save the path and the whole job in the needed analysis collection.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Regression Job from the Diastema playbook.
        - last_bucket (String): The path that the non analyzed data are saved.
        - algorithm (String): The algorithm to run.
        - tensorfow_algorithm (String): A tensorflow algorithm to run.

    Returns:
        - MinIO path (String): The path that the analyzed data are saved.
    """

    algorithms = {
        "linear regression" : False,                    # Not imported yet
        "generalized linear regression" : False,        # Not imported yet
        "decision tree regression" : "decisiontree",
        "random forest regression" : "randomforest",
        "gradient-boosted tree regression" : False      # Not imported yet
    }

    algorithm_to_use = ""
    default_job = "decision tree regression"
    if algorithm==False:
        algorithm_to_use = algorithms[default_job]
    else:
        if algorithm in algorithms:
            algorithm_to_use = algorithms[algorithm]
            if algorithm_to_use == False:
                algorithm_to_use = algorithms[default_job]
        else:
            algorithm_to_use = algorithms[default_job]
    
    # Path of regression in Diastema docker image
    analysis_path = "/app/src/RegressionJob.py"

    # Data Bucket = last jobs output bucket
    data_bucket = last_bucket

    # Analysis Bucket = User/analysis-id/job-step
    analysis_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/regressed-"+minioString(job["step"])

    # Jobs arguments
    job_args = [analysis_path, algorithm_to_use, data_bucket, analysis_bucket, job["column"]]

    # Make the MinIO Analysis buckers
    minio_client.put_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/regressed-"+minioString(job["step"])+"/", io.BytesIO(b""), 0,)

    # Make the Spark call
    spark_caller(job_args)

    # Remove the _SUCCESS file from the  spark job results
    minio_client.remove_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/regressed-"+minioString(job["step"])+"/_SUCCESS")

    # Insert the regressed data in MongoDB
    regression_job_record = {"minio-path":analysis_bucket, "directory-kind":"regressed-data", "job-json":job}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), regression_job_record)

    # Contact front end for the ending of the job
    # diastema_call(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"]), "regression")
    diastema_call(message = "update", update = "Regression executed.")

    # Return the bucket that this job made output to 
    return analysis_bucket

# Clustering Job
def clustering(playbook, job, last_bucket, algorithm=False, tensorfow_algorithm=False):
    """
    A function to handle a Clustering Analysis Job from the Diastema JSON playbook.
    It will setup the folders needed for the spark jobs in the MinIO Database.
    Then it will call the Spark Job after configuring the way that the job must be called.
    After the above, it will use the MongoDB to save the path and the whole job in the needed analysis collection.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Clustering Job from the Diastema playbook.
        - last_bucket (String): The path that the non analyzed data are saved.
        - algorithm (String): The algorithm to run.
        - tensorfow_algorithm (String): A tensorflow algorithm to run.

    Returns:
        - MinIO path (String): The path that the analyzed data are saved.
    """

    algorithms = {
        "k-means clustering" : "Kmeans",
        "generalized linear regression" : False,   # Not imported yet
        "decision tree regression" : False,        # Not imported yet
        "random forest regression" : False,        # Not imported yet
        "gradient-boosted tree regression" : False # Not imported yet
    }

    algorithm_to_use = ""
    default_job = "k-means clustering"
    if algorithm==False:
        algorithm_to_use = algorithms[default_job]
    else:
        if algorithm in algorithms:
            algorithm_to_use = algorithms[algorithm]
            if algorithm_to_use == False:
                algorithm_to_use = algorithms[default_job]
        else:
            algorithm_to_use = algorithms[default_job]

    # AVAILABLE
    ## Kmeans
    algorithm_to_use = ""
    if algorithm==False:
        algorithm_to_use = "Kmeans"
    else:
        algorithm_to_use = algorithm
    
    # Path of clustering in Diastema docker image
    analysis_path = "/app/src/ClusteringJob.py"

    # Data Bucket = last jobs output bucket
    data_bucket = last_bucket

    # Analysis Bucket = User/analysis-id/job-step
    analysis_bucket = minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"])+"/clustered-"+minioString(job["step"])

    # Jobs arguments
    job_args = [analysis_path, algorithm_to_use, data_bucket, analysis_bucket, job["column"]]

    # Make the MinIO Analysis buckets
    minio_client.put_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/clustered-"+minioString(job["step"])+"/", io.BytesIO(b""), 0,)

    # Make the Spark call
    spark_caller(job_args)

    # Remove the _SUCCESS file from the  spark job results
    minio_client.remove_object(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"])+"/clustered-"+minioString(job["step"])+"/_SUCCESS")

    # Insert the clustered data in MongoDB
    clustering_job_record = {"minio-path":analysis_bucket, "directory-kind":"clustered-data", "job-json":job}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), clustering_job_record)

    # Contact front end for the ending of the job
    # diastema_call(minioString(playbook["database-id"]), "analysis-"+minioString(playbook["analysis-id"]), "clustering")
    diastema_call(message = "update", update = "Clustering executed.")

    # Return the bucket that this job made output to 
    return analysis_bucket

# Visualization job
def visualize(playbook, job, last_bucket):
    """
    A function to handle a Vizualization Job from the Diastema JSON playbook.

    Args:
        - playbook (JSON): The Diastema playbook.
        - job (JSON): This Data Visualization Job from the Diastema playbook.
        - last_bucket (String): The path that the data to be visualised are saved.

    Returns:
        - testing-value (String): A value that will have a perpose after the Diastema visualization framework is ready.
    """
    # The Data to be visualised are saved in the bucket below
    visualization_path = last_bucket

    # Get the job kind based in the Diastema JSON playbook
    broke_bucket = visualization_path.split("/")
    job_done = broke_bucket[2].split("-")[0]
    job_kind = ""
    if(job_done == "loaded"):
        job_kind = "data-load"
    elif(job_done == "cleaned"):
        job_kind = "cleaning"
    elif(job_done == "classified"):
        job_kind = "classification"
    elif(job_done == "regressed"):
        job_kind = "regression"
    else:
        job_kind = "clustering"
    
    # get the step that the visualization Job came from
    step_to_visualize = job["from"]

    # Use all the playbook to find the last job
    jobs = playbook["jobs"]

    # the column to be visualized
    vis_column = ""

    for i_job in jobs:
        if(i_job["step"] == step_to_visualize):
            vis_column = i_job["column"].lower()
            break

    # Contact front end to make a visualization
    # diastema_call(last_bucket, job_kind)
    diastema_call(message = "visualize", visualization_path = last_bucket, job_name = job_kind, column = vis_column)
    
    # dummy return
    return "visualization-from: "+last_bucket

""" Functions used for the json handling """
# Request a job
def job_requestor(job_json, jobs_anwers_dict, playbook):
    """
    A function to handle a Vizualization Job from the Diastema JSON playbook.

    Args:
        - job_json (JSON): The job to request to be done.
        - jobs_anwers_dict (Dictionary): A dictionary holding all the return values of every 
            Diastema job done in the given analysis so far.
        - playbook (JSON): The Diastema playbook.

    Returns:
        - Nothing.
    """
    title = job_json["title"]
    step = job_json["step"]
    from_step = job_json["from"]
    
    if(title == "data-load"):
        jobs_anwers_dict[step] = data_load(playbook, job_json, job_json["files"])
    
    if(title == "cleaning"):
        jobs_anwers_dict[step] = cleaning(playbook, job_json, jobs_anwers_dict[from_step], max_shrink = job_json["max-shrink"])
    
    if(title == "classification"):
        jobs_anwers_dict[step] = classification(playbook, job_json, jobs_anwers_dict[from_step], algorithm = job_json["algorithm"])
    
    if(title == "regression"):
        jobs_anwers_dict[step] = regression(playbook, job_json, jobs_anwers_dict[from_step], algorithm = job_json["algorithm"])
    
    if(title == "clustering"):
        jobs_anwers_dict[step] = clustering(playbook, job_json, jobs_anwers_dict[from_step], algorithm = job_json["algorithm"])
    
    if(title == "visualize"):
        jobs_anwers_dict[step] = visualize(playbook, job_json, jobs_anwers_dict[from_step])
    
    return

# Access jobs by viewing them Depth-first O(N)
def jobs(job_step, jobs_dict, jobs_anwers_dict, playbook):
    """
    A Depth first recursive function, running every job of the Diastema analysis.

    Args:
        - job_step (Integer): The step of the job to parse.
        - jobs_dict (Dictionary): A Dictionary with every job from the requests.
        - jobs_anwers_dict (Dictionary): A dictionary holding all the return values of every 
            Diastema job done in the given analysis so far.
        - playbook (JSON): The Diastema playbook.

    Returns:
        - Nothing.
    """
    # Make the job request
    job_requestor(jobs_dict[job_step], jobs_anwers_dict, playbook)
    
    # Depth-first approach
    next_steps = jobs_dict[job_step]["next"]
    for step in next_steps:
        if(step != 0):  # If ther is no next job then do not try to go deeper
            jobs(step, jobs_dict, jobs_anwers_dict, playbook)
    return

# Handle the playbook
def handler(json_jobs, playbook):
    """
    A function to handle and run the Diastema playbook.

    Args:
        - json_jobs (JSON): The jobs of the playbook.
        - playbook (JSON): The Diastema playbook.

    Returns:
        - Nothing.
    """
    
    # handle jobs as a dictionary - O(N)
    jobs_dict = {}
    for job in json_jobs:
        jobs_dict[job["step"]] = job
    
    # Find starting jobs - O(N)
    starting_jobs = []
    for job_step, job in jobs_dict.items():
        # print(job_step, '->', job)
        if job["from"] == 0:
            starting_jobs.append(job_step)
    #print(starting_jobs)
    
    # Use a dictionary as a storage for each job answer
    jobs_anwers_dict = {}
    
    # for each starting job, start the analysis
    for starting_job_step in starting_jobs:
        job = jobs_dict[starting_job_step]
        # navigate through all the jobs and execute them in the right order
        jobs(starting_job_step, jobs_dict, jobs_anwers_dict, playbook)
    
    # Print jobs_anwers_dict for testing purposes
    for job_step, answer in jobs_anwers_dict.items():
        print(job_step, '->', answer)
    
    return

""" Socket-io General Events """
# An event to handle client's connection
@sio.event
def connect(sid, env):
    print("Client connected", sid)
    return
    
# An event to handle client's disconnection
@sio.event
def disconnect(sid):
    print("Client disconnected", sid)
    return

# An event to handle unknown events -> 404
@sio.on("*")
def catch_all(event, sid, data):
    print(f"{event} doesn't have a registered handler")
    return

""" Socket-io Analysis Events """
# An event for handling and using the JSON playbook
@sio.on("analysis")
def analysis(sid, data):
    """
    An endpoint to handle a Diastema Analysis playbook from start to finish.

    Args:
        - json_jobs (JSON): The jobs of the playbook.
        - playbook (JSON): The Diastema playbook.

    Returns:
        - responce (Responce): A responce to the central Diastema API Server containing information
            based on the analysis that has been requested.
    """
    print("Analysis Started", flush=True)
    # Get the JSON from the client
    # playbook = f"\n\n\nClient {sid} has spoken with {data['analysis']}\n\n\n"
    # playbook = json.loads(data['analysis'])
    playbook = data
    
    # Here there will probably be code to check the whole json
    # To return if there is a bad request
    
    # check if diastema token is right
    if playbook["diastema-token"] != diastema_token:
        print("Diastema Token is wrong", flush=True)
        return

    print("Starting Analysis Handler", flush=True)
    # Send the playbook for handling
    handler(playbook["jobs"], playbook)

    # Insert metadata in mongo
    print("Insert metadata in mongo", flush=True)
    metadata_json = playbook["metadata"]
    metadata_record = {"kind":"metadata", "metadata":metadata_json}
    insertMongoRecord(minioString(playbook["database-id"]), "analysis_"+minioString(playbook["analysis-id"]), metadata_record)

    # Contact front end for the ending of the analysis
    # diastema_call(minioString(playbook["database-id"])+"/analysis-"+minioString(playbook["analysis-id"]), "analysis")
    print("Contacting front end for the ending of the analysis", flush=True)
    diastema_call(message = "update", update = ("Analysis completed with ID: "+minioString(playbook["analysis-id"])))
    return 

""" Main """
# Main code
if __name__ == "__main__":
    app.run(HOST, PORT, True)
