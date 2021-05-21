import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from flask import Flask, Blueprint, jsonify, request
from flask_restplus import Api, Resource, fields
from werkzeug.utils import cached_property
import couchdb

import json

# couch = couchdb.Server('http://localhost:5984')
# db = couch.create('db_test')

app = Flask(__name__)
blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(blueprint, doc='/documentation') #,doc=False

app.register_blueprint(blueprint)

app.config['SWAGGER_UI_JSONEDITOR'] = True

a_language = api.model('Language', {'language' : fields.String('The language.')}) #, 'id' : fields.Integer('ID')
 
languages = []
python = {'language' : 'Python', 'id' : 1}
languages.append(python)

@api.route('/language')
class Language(Resource):

    @api.marshal_with(a_language, envelope='the_data')
    def get(self):
        # all_languages = db.view('_all_docs', include_docs=True)
        print('got a get request')
        return 'ok'

    @api.expect(a_language)
    def post(self):
        new_language = api.payload 
        # db.save(new_language)
        #new_language['id'] = len(languages) + 1
        #languages.append(new_language)
        return {'result' : 'Language added'}, 201 

class Database:

    def __init__(self):
        self.data = {
            'word_lengths_by_city': {
                "melbourne": 3.3,
                "adelaide": 2.7,
                "sydney": 4.2,
                "darwin": 1.8,
                "perth": 5.3,
            },

            'unemployment_pct_by_city': {
                "melbourne": 1.0,
                "adelaide": 2.0,
                "sydney": 4.0,
                "darwin": 3.0,
                "perth": 5.0,
            }
        }
    
    def fetch_view(self, view: str):
        return self.data[view] if view in self.data else None

db = Database()

def fetch_tag(tag, datasets):
    return tag

@app.route('/testdata')
def testdata():
    xattr = request.args.get('xattr') or 'unemployment_pct_by_city'
    yattr = request.args.get('yattr') or 'word_lengths_by_city'
    tags = request.args.get('tag') or ['city_name']
    
    print(f'xattr: {xattr}')
    print(f'yattr: {yattr}')
    print(f'tags: {tags}')

    # http://haliax.local:5001/testdata?xattr=foo&yattr=bar&tag=a&tag=b&tag=c

    xdata = db.fetch_view(xattr)
    ydata = db.fetch_view(yattr)

    data = [
        {
            'tags': {
                tag : fetch_tag(tag, { xattr: xdata[city], yattr: ydata[city] })
                for tag in tags
            },
            'x': xdata[city],
            'y': ydata[city]
        }
        for city in set(xdata.keys()) & set(ydata.keys())
    ]

    response = jsonify({
        'data': data
    })

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


if __name__ == '__main__':
    app.run(debug=True)
