# Server

import socket 
import threading
import json
import os

SERVER = os.getenv("SERVER", "0.0.0.0")
PORT = int(os.getenv("PORT", 6006))

HEADER = 64
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

# A function to handle spark calls
def spark_call(msg):
    json_attrs = json.loads(msg)
    # print(json_attrs["column"])
    
    cmd  = 'spark-submit '
    cmd += '--master k8s://https://'+json_attrs["master-host"]+':'+json_attrs["master-port"]+' '
    cmd += '--deploy-mode cluster '
    cmd += '--name '+json_attrs["app-name"]+' '
    cmd += '--conf spark.executorEnv.MINIO_HOST="'+json_attrs["minio-host"]+'" '
    cmd += '--conf spark.executorEnv.MINIO_PORT="'+json_attrs["minio-port"]+'" '
    cmd += '--conf spark.executorEnv.MINIO_USER="'+json_attrs["minio-user"]+'" '
    cmd += '--conf spark.executorEnv.MINIO_PASS="'+json_attrs["minio-pass"]+'" '
    cmd += '--conf spark.app.name='+json_attrs["app-name"]+' '
    cmd += '--conf spark.kubernetes.authenticate.driver.serviceAccountName=spark '
    cmd += '--conf spark.kubernetes.container.image=docker.io/konvoulgaris/diastema-daas-analytics-catalogue:dev '
    cmd += json_attrs["path"]+' '
    cmd += json_attrs["algorithm"]+' '
    cmd += json_attrs["minio-input"]+' '
    cmd += json_attrs["minio-output"]+' '
    cmd += json_attrs["column"]+' '
    print(cmd)
    os.system(cmd)
    return

# Function to handle clients
def handle_client(conn, addr):
    # New connection accepted.
    print(f"[NEW CONNECTION] {addr} connected.")

    msg_length = conn.recv(HEADER).decode(FORMAT)
    if msg_length:
        msg_length = int(msg_length)
        msg = conn.recv(msg_length).decode(FORMAT)
        # print(f"[{addr}] {msg}")
        spark_call(msg)
        conn.send("Msg received".encode(FORMAT))

    # Close the connection
    conn.close()
    return
        
# Function to start the server and let it listen for new connections
def start():
    server.listen()
    print(f"[LISTENING] Server is listening on {SERVER}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")
    return

# Server Srartup
print("[STARTING] server is starting...")
start()