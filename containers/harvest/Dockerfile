FROM python:3.10.0a7-buster

ADD harvest.py .

RUN pip install --proxy=http://wwwproxy.unimelb.edu.au:8000 tweepy
RUN pip install --proxy=http://wwwproxy.unimelb.edu.au:8000 couchdb

CMD [ "python", "./harvest.py"]