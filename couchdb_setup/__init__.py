import couchdb

from os import listdir, path
from contextlib import contextmanager
from json import dumps

def compare_generated_existing(couch, db, doc, generated):
  from subprocess import call
  from tempfile import NamedTemporaryFile
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

def generate_design_docs(host, port, user, password):
  couch_url = f'https://{user}:{password}@{host}:{port}/'

  couch = couchdb.Server(couch_url)
  couch.resource.session.disable_ssl_verification()


  for db, name, doc in gen_design_docs():
    docid = f'_design/{name}'
    print(f'{db}/{docid}')
    doc |= {
      '_id' : docid,
      'language' : 'javascript',
    }
    if docid in couch[db]:
      doc['_rev'] = couch[db][docid]['_rev']
      print('update')
      couch[db][docid] = doc
    else:
      print('save')
      couch[db].save(doc)
    # compare_generated_existing(couch, db, name, doc)

def gen_view(prefix, name):
  contents = listdir(path.join(prefix, name))
  file_property_map = { 'map' : 'map.js', 'reduce' : 'reduce.js' }
  view = {}
  for prop, file in file_property_map.items():
    if file in contents:
      with open(path.join(prefix, name, file), 'r') as f:
        view[prop] = f.read()
  return view

def gen_design_doc(prefix, name):
  return {
    'views': {
      view: gen_view(path.join(prefix, name), view)
      for view in subdirs(path.join(prefix, name))
    }
  }

def subdirs(p=None):
  for f in listdir(p):
    if path.isdir(path.join(p, f) if p else f):
      yield f

# yields (db, doc_name, doc)
def gen_design_docs():
  for db in subdirs('design'):
    docs = {
      name : gen_design_doc(path.join('design', db), name)
      for name in subdirs(path.join('design', db))
    }
    for name, definition in docs.items():
      # 1. Create db if it doesn't exist
      # 2. What to do if the design doc already exists? update?
      yield (db, name, definition)

if __name__ == '__main__':
  print('searching for design docs')
  for db, name, doc in gen_design_docs():
    print()
    print(f'--- {db}/{name}')
    print(dumps(doc, indent=1, sort_keys=True))