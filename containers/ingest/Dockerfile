FROM python:3.10.0a7-buster

ADD ingest_aurin.py .

RUN pip install couchdb

CMD [ "python", "./ingest_aurin.py"]