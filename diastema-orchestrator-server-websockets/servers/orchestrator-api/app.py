import os
from flask import Flask, request, Response, make_response
from flask_cors import CORS
import socketio

""" Environment Variables """
# Flask app Host and Port
HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 4999))

# Diastema Orchestrator websocket Server Host and Port
ORCHESTRATOR_HOST = os.getenv("ORCHESTRATOR_HOST", "localhost")
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", 5000))

# Diastema Token Environment
DIASTEMA_KEY = os.getenv("DIASTEMA_KEY", "diastema-key")

""" Global variables """
# The name of the flask app
app = Flask(__name__)
CORS(app, resources={r"*": {"origins": "*"}})

# Diastema Token
diastema_token = DIASTEMA_KEY

""" Flask endpoints """
# An endpoint to call the Diastema Orchestrator websocket Server
@app.route("/analysis", methods=["POST"])
def analysis():
    playbook = request.json
    
    if playbook["diastema-token"] != diastema_token:
        return Response('{"reason": "diastema token is wrong"}', status=401, mimetype='application/json')
    
    # Send data to webserver without recovering data
    sio = socketio.Client()
    sio.connect("http://"+ORCHESTRATOR_HOST+":"+str(ORCHESTRATOR_PORT))
    sio.emit("analysis", {"analysis": playbook}) # Tell orchestrator that loading is done
    sio.disconnect()
    
    return Response(status=202)

@app.route("/analysis", methods=["OPTIONS"])
def analysis_options():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

""" Main """
# Main code
if __name__ == "__main__":
    app.run(HOST, PORT, True)