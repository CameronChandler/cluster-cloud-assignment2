import couchdb
import json

# set up connection to remote couchdb
remote_couch = couchdb.Server('https://admin:answering_railcar@172.26.133.242:6984/')
remote_couch.resource.session.disable_ssl_verification()

# ingest employment data
try:
    db = remote_couch.create('aurin_employment')

except Exception as e:
    remote_couch.delete('aurin_employment')
    db = remote_couch.create('aurin_employment')

with open('res/data_education_employment.json', encoding='utf8') as f:
    employments = json.load(f)["features"]
    for employment in employments:
        db.save(employment)