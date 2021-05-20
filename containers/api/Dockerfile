FROM python:3.8-slim-buster

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

ADD app/app.py .

COPY app/requirements.txt app/requirements.txt

# Need proxy here bc docker apparently doesn't pass this down from it's build env
RUN pip install --proxy=http://wwwproxy.unimelb.edu.au:8000 -r app/requirements.txt

EXPOSE 5000

COPY . .

CMD ["flask", "run"]
