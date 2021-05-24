import couchdb
import json

# set up connection to remote couchdb
remote_couch = couchdb.Server('https://admin:answering_railcar@172.26.133.242:6984/')
remote_couch.resource.session.disable_ssl_verification()

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