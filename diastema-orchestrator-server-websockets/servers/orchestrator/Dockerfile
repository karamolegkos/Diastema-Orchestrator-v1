FROM python:3.8

RUN apt update -y
RUN apt upgrade -y

WORKDIR /app

RUN pip3 install flask
RUN pip3 install requests
RUN pip3 install minio
RUN pip3 install pymongo
RUN pip install gunicorn
RUN pip install python-socketio==4.6.0
RUN pip install python-socketio[client]
RUN pip install gevent-websocket
RUN pip install gevent

COPY . .

CMD ["gunicorn", "-k", "gevent", "-b", "0.0.0.0:5000", "app:app"]