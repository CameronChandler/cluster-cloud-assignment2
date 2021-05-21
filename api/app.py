import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from flask import Flask, Blueprint, jsonify, request
from flask_restplus import Api, Resource, fields
from werkzeug.utils import cached_property
import couchdb

import json

remote_couch = couchdb.Server('https://admin:answering_railcar@118.138.238.242:6984/')
remote_couch.resource.session.disable_ssl_verification()
db = remote_couch['db_small_twitter']


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
        self.data = {'unemployment_pct_by_city': {
                "melbourne": 1.0,
                "adelaide": 2.0,
                "sydney": 4.0,
                "darwin": 3.0,
                "perth": 5.0,
            },
        'word_lengths_by_city': self.get_word_lengths_by_city()
        }
    
    def get_word_lengths_by_city(self):
        cities = {}
        word_lengths_by_city = {}
        for item in db.view('wordLengths/new-view', group=True):
            if item.key[0] in cities:
                cities[item.key[0]]['total_word_length'] += item.value * item.key[1]
                cities[item.key[0]]['tweet_count'] += item.value
            else:
                cities[item.key[0]] = {'total_word_length': item.value * item.key[1], 'tweet_count': item.value}

        for city_name in cities.keys():
            word_lengths_by_city[city_name] = cities[city_name]['total_word_length'] / cities[city_name]['tweet_count']
        
        return word_lengths_by_city

    def fetch_view(self, view: str):
        return self.data[view] if view in self.data else None

local_db = Database()

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

    xdata = local_db.fetch_view(xattr)
    ydata = local_db.fetch_view(yattr)

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