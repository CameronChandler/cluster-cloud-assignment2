import couchdb
import json

from os import environ

COUCHDB_USER=environ['COUCHDB_USER']
COUCHDB_PASSWORD=environ['COUCHDB_PASSWORD']
COUCHDB_HOST=environ['COUCHDB_HOST']

couch_url = f'http://{COUCHDB_USER}:{COUCHDB_PASSWORD}@{COUCHDB_HOST}:5984/'
# use 5984 in container cluster
# use 6984 on local machine

# set up connection to remote couchdb
remote_couch = couchdb.Server(couch_url)
# remote_couch.resource.session.disable_ssl_verification()
# when using port 6984 when ssl is involved

# ingest employment data
try:
    db_employment = remote_couch.create('aurin_employment')

    with open('res/data_education_employment.json', encoding='utf8') as f:
        employments = json.load(f)["features"]
        for employment in employments:
            db_employment.save(employment)

except BaseException as e:
    print('Error on ingesting aurin employment: ', str(e))

# ingest income data
try:
    db_income = remote_couch.create('aurin_income')

    with open('res/data_income.json', encoding='utf8') as f:
        incomes = json.load(f)["features"]
        for income in incomes:
            db_income.save(income)

except BaseException as e:
    print('Error on ingesting aurin income: ', str(e))