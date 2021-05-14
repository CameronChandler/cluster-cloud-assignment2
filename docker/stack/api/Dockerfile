FROM python:3.8-slim-buster

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

ADD app/app.py .

COPY app/requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

EXPOSE 5000

COPY . .

CMD ["flask", "run"]
