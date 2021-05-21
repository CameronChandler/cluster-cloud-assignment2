import couchdb
import json

# set up connection to remote couchdb
remote_couch = couchdb.Server('https://admin:answering_railcar@118.138.238.242:6984/')
remote_couch.resource.session.disable_ssl_verification()

# ingest small twitter data
try:
    db = remote_couch.create('db_small_twitter')

except Exception as e:
    remote_couch.delete('db_small_twitter')
    db = remote_couch.create('db_small_twitter')

with open('res/smallTwitter.json', encoding='utf8') as f:
    tweets = json.load(f)["rows"]
    for tweet in tweets:
        db.save(tweet)