import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property
from flask import Flask, Blueprint, jsonify, request
from werkzeug.utils import cached_property
import couchdb

remote_couch = couchdb.Server('https://admin:answering_railcar@118.138.238.242:6984/')
remote_couch.resource.session.disable_ssl_verification()
twitter_db = remote_couch['db_small_twitter']
income_db = remote_couch['aurin_income']
employment_db = remote_couch['aurin_employment']

app = Flask(__name__)

class Database:

    def __init__(self):
        self.data = {
            'income_by_city': self.get_income_by_city(),
            'word_lengths_by_city': self.get_word_lengths_by_city(),
            'non_school_by_city': self.get_non_school_by_city(),
            'unemployment_by_city': self.get_unemployment_by_city()
        }

    def translate_city_name(self, name):
        name_translations = {'Greater Melbourne': 'melbourne', 'Greater Sydney': 'sydney', 'Greater Adelaide': 'adelaide',\
                            'Greater Brisbane': 'brisbane', 'Greater Hobart': 'hobart', 'Greater Darwin': 'darwin'}
        if name in name_translations:
            return name_translations[name]
        else:
            return name
    
    def get_word_lengths_by_city(self):
        cities = {}
        word_lengths_by_city = {}
        for item in twitter_db.view('wordLengths/new-view', group=True):
            if item.key[0] in cities:
                cities[item.key[0]]['total_word_length'] += item.value * item.key[1]
                cities[item.key[0]]['tweet_count'] += item.value
            else:
                cities[item.key[0]] = {'total_word_length': item.value * item.key[1], 'tweet_count': item.value}

        for city_name in cities.keys():
            word_lengths_by_city[city_name] = cities[city_name]['total_word_length'] / cities[city_name]['tweet_count']
        
        return word_lengths_by_city

    def get_income_by_city(self):
        cities = {}
        for item in income_db.view('median_income/income-view'):
            city_name = self.translate_city_name(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        return cities

    def get_non_school_by_city(self):
        cities = {}
        for item in employment_db.view('education/non-school'):
            city_name = self.translate_city_name(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        return cities

    def get_unemployment_by_city(self):
        cities = {}
        for item in employment_db.view('employment/unemployment-rate'):
            city_name = self.translate_city_name(item.key)
            if city_name not in cities:
                cities[city_name] = item.value
        return cities

    def fetch_view(self, view: str):
        return self.data[view] if view in self.data else None

local_db = Database()

def fetch_tag(tag, datasets):
    return tag

@app.route('/testdata')
def testdata():
    xattr = request.args.get('xattr') or 'income_by_city'
    yattr = request.args.get('yattr') or 'non_school_by_city' #'word_lengths_by_city'
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
                tag : city
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