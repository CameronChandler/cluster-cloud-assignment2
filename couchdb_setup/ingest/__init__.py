import couchdb
import json
from os import path

from log import *

def map_aurin_data(data):
  return data['features']

def map_twitter_data(data):
  docs = [item['doc'] for item in data]
  for doc in docs:
    del doc['_id']
    del doc['_rev']
  return docs


def ingest(host, port, user, password, data_dir, batch_size=512):
  couch_url = f'https://{user}:{password}@{host}:{port}/'

  couch = couchdb.Server(couch_url)
  couch.resource.session.disable_ssl_verification()

  dbs = {
    'aurin_employment': (path.join(data_dir, 'data_education_employment.json'), map_aurin_data),
    'aurin_income': (path.join(data_dir, 'data_income.json'), map_aurin_data),
    'tweets_db': (path.join(data_dir, 'data_tweets_db.json'), map_twitter_data)
  }

  for db_name, (file, mapper) in dbs.items():
    clear_and_create_db(couch, db_name)
    with open(file, encoding='utf-8') as f:
      data = mapper(json.load(f)) if mapper else json.load(f)

      trace(f'loaded {file} for {db_name}')

      offset = 0
      while offset < len(data):
        results = couch[db_name].update(data[offset:offset+batch_size])
        for i, (success, docid, recv_or_exc) in enumerate(results):
          if not success:
            print(data[i])
            print(f'failed to update document: {recv_or_exc}')
            if not input('continue? ') == 'y':
              return
        offset += batch_size
        trace(f'uploaded {offset+batch_size} documents')
      # for doc in data:
      #   couch[db_name].save(doc)

def clear_and_create_db(couch, db_name):
  try:
    db = couch.create(db_name)
  except Exception as e:
    error(f'Failed to create {db_name}: {e}')
    if input('delete the existing db? ') == 'y':
      couch.delete(db_name)
      db = couch.create(db_name)
      input('database cleared. press enter to continue')