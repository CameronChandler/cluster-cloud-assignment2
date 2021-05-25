import couchdb
import json
from os import path

def ingest(host, port, user, password, data_dir):
  couch_url = f'https://{user}:{password}@{host}:{port}/'

  couch = couchdb.Server(couch_url)
  couch.resource.session.disable_ssl_verification()

  dbs = {
    'aurin_employment': path.join(data_dir, 'data_education_employment.json'),
    'aurin_income': path.join(data_dir, 'data_income.json'),
  }

  for db_name, file in dbs.items():
    with open(file, encoding='utf-8') as f:
      features = json.load(f)['features']
      trace(f'loaded {file} for {db_name}')
      for feature in features:
        db.save(feature)

def clear_and_create_db(db_name):
  try:
    db = couch.create(db_name)
  except Exception as e:
    couch.delete(db_name)
    db = couch.create(db_name)