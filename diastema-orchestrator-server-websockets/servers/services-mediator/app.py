import os
from flask import Flask, request, Response, make_response
import socketio
import requests

# Make Client
sio = socketio.Client()

""" Environment Variables """
# Flask app Host and Port
HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 5000))

# Diastema Orchestrator websocket Server Host and Port
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", 5000))

# Services Host and Port 
SERVICES_HOST = os.getenv("SERVICES_HOST", "localhost")
SERVICES_PORT = int(os.getenv("SERVICES_PORT", 5000))

""" Global variables """
# The name of the flask app
app = Flask(__name__)
sio.connect("http://"+SERVICES_HOST+":"+str(SERVICES_PORT))

""" Flask endpoints """
@app.route("/loading", methods=["POST"])
def loading():
    loading_data = request.json
    sio.emit("data-loading", loading_data) # Call Data loading
    return Response(status=200)

@app.route("/cleaning", methods=["POST"])
def cleaning():
    cleaning_data = request.json
    sio.emit("data-cleaning", cleaning_data) # Call Data Cleaning
    return Response(status=200)
    
""" Socket io Client Events """
@sio.on("data-loading-done")
def data_loading_done(data):
    print("I GOT THAT LOADING IS DONE")
    job = data
    url = "http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT)+"/data-loading-done"
    resp = requests.post(url, json=job)
    print("LOADING: I ended")
    return

@sio.on("data-cleaning-done")
def data_cleaning_done(data):
    print("I GOT THAT CLEANING IS DONE")
    job = data
    url = "http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT)+"/data-cleaning-done"
    resp = requests.post(url, json=job)
    print("CLEANING: I ended")
    return

""" Main """
# Main code
if __name__ == "__main__":
    app.run(HOST, PORT, True)