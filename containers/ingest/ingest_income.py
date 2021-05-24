import couchdb
import json

# set up connection to remote couchdb
remote_couch = couchdb.Server('https://admin:answering_railcar@172.26.133.242:6984/')
remote_couch.resource.session.disable_ssl_verification()

# ingest income data
try:
    db = remote_couch.create('aurin_income')

except Exception as e:
    remote_couch.delete('aurin_income')
    db = remote_couch.create('aurin_income')

with open('res/data_income.json', encoding='utf8') as f:
    incomes = json.load(f)["features"]
    for income in incomes:
        db.save(income)