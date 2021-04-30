FROM python:3.10.0a7-buster

ADD harvest.py .
ADD credential.py .

RUN pip install tweepy

CMD [ "python", "./harvest.py"]