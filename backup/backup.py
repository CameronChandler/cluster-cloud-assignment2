import couchdb
import json
from os import environ

"""COUCHDB_BACKUP_SOURCE_USER = environ['COUCHDB_BACKUP_SOURCE_USER']
COUCHDB_BACKUP_SOURCE_PASSWORD = environ['COUCHDB_BACKUP_SOURCE_PASSWORD']
COUCHDB_BACKUP_SOURCE_HOST = environ['COUCHDB_BACKUP_SOURCE_HOST']
COUCHDB_BACKUP_SOURCE_DB_NAME = environ['COUCHDB_BACKUP_SOURCE_DB_NAME']

COUCHDB_BACKUP_DEST_USER = environ['COUCHDB_BACKUP_DEST_USER']
COUCHDB_BACKUP_DEST_PASSWORD = environ['COUCHDB_BACKUP_DEST_PASSWORD']
COUCHDB_BACKUP_DEST_HOST = environ['COUCHDB_BACKUP_DEST_HOST']
COUCHDB_BACKUP_DEST_DB_NAME = environ['COUCHDB_BACKUP_DEST_DB_NAME']

source_couch_url = f'http://{COUCHDB_BACKUP_SOURCE_USER}:{COUCHDB_BACKUP_SOURCE_PASSWORD}@{COUCHDB_BACKUP_SOURCE_HOST}:6984/ '
source_couch = couchdb.Server(source_couch_url)
source_couch.resource.session.disable_ssl_verification()

dest_couch_url = f'http://{COUCHDB_BACKUP_DEST_USER}:{COUCHDB_BACKUP_DEST_PASSWORD}@{COUCHDB_BACKUP_DEST_HOST}:6984/'
dest_couch = couchdb.Server(source_couch_url)
dest_couch.resource.session.disable_ssl_verification()

"""

source_couch = couchdb.Server('https://admin:answering_railcar@118.138.238.242:6984/')
source_couch.resource.session.disable_ssl_verification()

dest_couch = couchdb.Server('https://admin:answering_railcar@172.26.133.242:6984/')
dest_couch.resource.session.disable_ssl_verification()

try:
    db_source = source_couch['db_test']

except BaseException as e:
    print("Error: ", str(e))
    exit()

try:
    db_dest = dest_couch['db_test']

except BaseException as e:
    db_dest = dest_couch.create('db_test')

for document in db_source.view('_all_docs', include_docs=True):
    data = document['doc']
    del data['_id']
    del data['_rev']
    db_dest.save(data)
    print(data)