import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from flask import Flask, Blueprint, jsonify, request
from werkzeug.utils import cached_property
import couchdb

COORDINATES = {'canberra':  [149.13, -35.28],
               'melbourne': [144.96, -37.81],
               'sydney':    [151.21, -33.87],
               'brisbane':  [153.03, -27.47],
               'darwin':    [130.84, -12.46],
               'perth':     [115.86, -31.95],
               'adelaide':  [138.60, -34.93],
               'hobart':    [147.33, -42.88]}

from os import environ

COUCHDB_USER=environ['COUCHDB_USER']
COUCHDB_PASSWORD=environ['COUCHDB_PASSWORD']
COUCHDB_HOST=environ['COUCHDB_HOST']

couch_url = f'http://{COUCHDB_USER}:{COUCHDB_PASSWORD}@{COUCHDB_HOST}:5984/'

print(f'couch_url: {couch_url}')
remote_couch = couchdb.Server(couch_url)
remote_couch.resource.session.disable_ssl_verification()

def twitter_db():
    return remote_couch['tweets_db']
def income_db():
    return remote_couch['aurin_income']
def employment_db():
    return remote_couch['aurin_employment']

app = Flask(__name__)

class Database:

    def __init__(self):
        self.data = {
            'median_income_by_city': self.get_median_income_by_city,
            'word_lengths_by_city': self.get_word_lengths_by_city,
            'non_school_qualifications_by_city': self.get_non_school_qualifications_by_city,
            'unemployment_pct_by_city': self.get_unemployment_pct_by_city,
        }

    def translate_city_name_from_couch_to_ui(self, name):
        name = name.lower().removeprefix('greater').strip()
        known_cities = {
            'melbourne',
            'sydney',
            'adelaide',
            'brisbane',
            'hobart',
            'darwin',
            'australian capital territory',
            'perth',
        }
        if name not in known_cities:
            return None

        rename_cities = {
            'australian capital territory' : 'canberra'
        }
        name = rename_cities[name] if name in rename_cities else name

        return name

    def get_word_lengths_by_city(self):
        cities = {}
        word_lengths_by_city = {}
        for item in twitter_db().view('word-lengths/new-view', group=True):
            if item.key[0] in cities:
                cities[item.key[0]]['total_word_length'] += item.value * item.key[1]
                cities[item.key[0]]['tweet_count'] += item.value
            else:
                cities[item.key[0]] = {'total_word_length': item.value * item.key[1], 'tweet_count': item.value}

        for city_name in cities.keys():
            word_lengths_by_city[self.translate_city_name_from_couch_to_ui(city_name)] = cities[city_name]['total_word_length'] / cities[city_name]['tweet_count']
        print("word_lengths_by_city")
        print(word_lengths_by_city)
        return word_lengths_by_city

    def get_median_income_by_city(self):
        cities = {}
        for item in income_db().view('median_income/income-view'):
            city_name = self.translate_city_name_from_couch_to_ui(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        print("median income")
        print(cities)
        return cities

    def get_non_school_qualifications_by_city(self):
        cities = {}
        for item in employment_db().view('education/non-school'):
            city_name = self.translate_city_name_from_couch_to_ui(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        return cities

    def get_unemployment_pct_by_city(self):
        cities = {}
        for item in employment_db().view('employment/unemployment-rate'):
            city_name = self.translate_city_name_from_couch_to_ui(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        print("unemployment")
        print(cities)
        return cities

    def fetch_view(self, view: str):
        if view not in self.data:
            return None

        result = self.data[view]()
        if None in result:
            del result[None]
        return result

local_db = Database()

@app.route('/graphkeys')
def graphkeys():
    attr = request.args.get('attr') or 'unemployment_pct_by_city'
    tags = request.args.get('tag') or ['city_name']
    tags = [tags] if isinstance(tags, str) else tags
    
    print(f'xattr: {attr}')
    print(f'tags: {tags}')

    ATTRIBUTES = {'median_income_by_city': {'text': 'Income', 'label': 'Median Income ($)'},
                  'unemployment_pct_by_city': {'text': 'Unemployment', 'label': 'Unemployment (%)'},
                  'non_school_qualifications_by_city': {'text': 'Higher Education', 'label': 'Population with Non-School Qualifications (%)'},
                  'word_lengths_by_city': {'text': 'Average Word Length', 'label': 'Ave. Word Length (From Tweets)'}}

    response = jsonify(ATTRIBUTES[attr])

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

@app.route('/chartdata')
def testdata():
    xattr = request.args.get('xattr') or 'unemployment_pct_by_city'
    yattr = request.args.get('yattr') or 'word_lengths_by_city'
    
    print(f'xattr: {xattr}')
    print(f'yattr: {yattr}')

    # http://haliax.local:5001/testdata?xattr=foo&yattr=bar&tag=a&tag=b&tag=c

    xdata = local_db.fetch_view(xattr)
    print("XDATA")
    print(xdata)
    ydata = local_db.fetch_view(yattr)

    data = [
        {
            'tags': {
                'city_name': city.capitalize(),
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


def label(attr, val):
    if attr == 'median_income_by_city':
        return f'Median Income: ${int(val):,}'
    if attr == 'unemployment_pct_by_city':
        return f'Unemployment: {val}%'
    if attr == 'non_school_qualifications_by_city':
        return f'Persons with Non-School Qualifications: {val}%'
    if attr == 'word_lengths_by_city':
        return f'word_lengths_by_city: {val} characters'
    return 'Missing Data'

@app.route('/mapdata')
def mapdata():
    xattr = request.args.get('xattr') or 'unemployment_pct_by_city'
    
    print(f'xattr: {xattr}')

    xdata = local_db.fetch_view(xattr)

    geodata = {"type": "geojson",
            "data": {
                "type": "FeatureCollection",
                'features': [
                    {
                        'type': 'Feature',
                        'properties': {
                            'description': f'<strong>{city.capitalize()}</strong><p>{label(xattr, city_data)}</p>',
                            'x': city_data
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': COORDINATES[city]
                        }
                    }
                for city, city_data in xdata.items()]
            }
    }

    data = {city.capitalize(): x for city, x in xdata.items()}
    
    response = jsonify({
        'geodata': geodata,
        'data': data,
        'cities': ['Canberra', 'Melbourne', 'Sydney', 'Brisbane', 
                   'Darwin', 'Perth', 'Adelaide', 'Hobart']
    })

    response.headers.add('Access-Control-Allow-Origin', '*')

    return response

if __name__ == '__main__':
    app.run(debug=True)