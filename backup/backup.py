import couchdb
from json import dumps
from os import environ, path, environ
from sys import stdout

COUCHDB_USER=environ['COUCHDB_USER']
COUCHDB_PASSWORD=environ['COUCHDB_PASSWORD']
COUCHDB_HOST=environ['COUCHDB_HOST']

RES_DIR=path.join('couchdb_setup', 'ingest', 'res')

db_file_map = {
  'db_test' : path.join(RES_DIR, 'data_db_test.json'),
  # 'db_small_twitter' : path.join(RES_DIR, 'data_db_small_twitter.json'),
  'tweets_db' : path.join(RES_DIR, 'data_tweets_db.json')
}

def couch_backup_local(couch, db, writer):
  '''
  Pull a whole database from Couch and write it to a local file
  '''
  count = 0
  batch_size=256
  writer.write('[')
  for document in couch[db].iterview('_all_docs', batch=batch_size, include_docs=True):
    if count > 0:
      writer.write(',')
    writer.write('\n')
    writer.write(dumps(document, indent=1))
    count += 1
    if count % batch_size == 0:
      print(f'backed up {count} documents', end='\r')
  writer.write('\n]\n')
  print(f'backed up {count} documents', end='\r')
  print()

if __name__ == '__main__':
  server = couchdb.Server(f'https://{COUCHDB_USER}:{COUCHDB_PASSWORD}@{COUCHDB_HOST}:6984/')
  server.resource.session.disable_ssl_verification()
  for db, file in db_file_map.items():
    with open(file, 'w') as f:
      couch_backup_local(server, db, f)

