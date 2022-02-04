FROM python:3.8

RUN apt update -y
RUN apt upgrade -y

WORKDIR /app

RUN pip3 install flask
RUN pip3 install requests
RUN pip3 install minio
RUN pip install gunicorn

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]