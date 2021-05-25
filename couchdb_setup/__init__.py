import couchdb

from os import listdir, path
from contextlib import contextmanager
from json import dumps
from subprocess import call
from tempfile import NamedTemporaryFile

from .ingest import ingest as ingest_inner

from log import *

@prompt('Update design docs')
@traced('CouchDB')
def generate_design_docs(host, port, user, password):
  couch_url = f'https://{user}:{password}@{host}:{port}/'

  couch = couchdb.Server(couch_url)
  couch.resource.session.disable_ssl_verification()

  ensure_dbs_exist(couch)

  for db, name, doc in _gen_design_docs():
    docid = f'_design/{name}'
    trace(f'{db}/{docid}')
    doc |= {
      '_id' : docid,
      'language' : 'javascript',
    }
    if docid in couch[db]:
      doc['_rev'] = couch[db][docid]['_rev']
      trace('update')
      couch[db][docid] = doc
    else:
      trace('save')
      couch[db].save(doc)
    # _compare_generated_existing(couch, db, name, doc)

@prompt('Import local data into couch (this will remove any existing data)')
@traced('CouchDB')
def ingest(host, port, user, password, data_dir):
  ingest_inner(host, port, user, password, data_dir)

def ensure_dbs_exist(couch):
  for db in subdirs('design'):
    try:
      couch.create(db)
    except couchdb.PreconditionFailed as e:
      pass

def _compare_generated_existing(couch, db, doc, generated):
  fetched = NamedTemporaryFile('w')
  fetched_doc = couch[db].get('_design/' + doc)
  del fetched_doc['_rev']
  fetched_doc = dumps(fetched_doc, indent=1, sort_keys=True)
  fetched.write(fetched_doc)
  fetched.flush()
  gend = NamedTemporaryFile('w')
  gend.write(dumps(generated, indent=1, sort_keys=True))
  gend.flush()
  print()
  print(f'--- {db}/_design/{doc}')
  print(f'--- {fetched.name} vs {gend.name}')
  # print(fetched_doc)
  # print('-------')
  # print(generated)
  call([
    'diff',
    fetched.name,
    gend.name
  ])

def _gen_view(prefix, name):
  contents = listdir(path.join(prefix, name))
  file_property_map = { 'map' : 'map.js', 'reduce' : 'reduce.js' }
  view = {}
  for prop, file in file_property_map.items():
    if file in contents:
      with open(path.join(prefix, name, file), 'r') as f:
        view[prop] = f.read()
  return view

def _gen_design_doc(prefix, name):
  return {
    'views': {
      view: _gen_view(path.join(prefix, name), view)
      for view in subdirs(path.join(prefix, name))
    }
  }

def subdirs(p=None):
  for f in listdir(p):
    if path.isdir(path.join(p, f) if p else f):
      yield f

# yields (db, doc_name, doc)
def _gen_design_docs():
  for db in subdirs('design'):
    docs = {
      name : _gen_design_doc(path.join('design', db), name)
      for name in subdirs(path.join('design', db))
    }
    for name, definition in docs.items():
      yield (db, name, definition)

if __name__ == '__main__':
  print('searching for design docs')
  for db, name, doc in _gen_design_docs():
    print()
    print(f'--- {db}/{name}')
    print(dumps(doc, indent=1, sort_keys=True))