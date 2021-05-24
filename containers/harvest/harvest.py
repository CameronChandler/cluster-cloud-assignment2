import tweepy
import couchdb
import json
import credentials


class TwitterAuth:
    # This class handles functions and attributes for authenticating twitter api

    def get_twitter_auth(self):
        # function create and return an authentication object
        auth = tweepy.OAuthHandler(credentials.consumer_key, credentials.consumer_secret)
        auth.set_access_token(credentials.access_token, credentials.access_token_secret)
        return auth


class TwitterStreamer:
    # This class handles the connection and streaming of live tweets
    def __init__(self):
        self.twitter_auth = TwitterAuth()
        self.harvest_count = 0  # initialise a harvest count int to know when to stop harvesting

    def stream_tweets(self):
        # This handles Twitter authentication and the connection to Twitter Streaming API
        listener = TwitterListener()
        auth = self.twitter_auth.get_twitter_auth()  # get authentication object from Auth Class
        stream = tweepy.Stream(auth, listener)  # initialise streaming
        stream.filter(locations=[113.6594, -43.00311, 153.61194, -12.46113],
                      languages=["en"])  # only getting tweets from within australia and tweets in english


class TwitterListener(tweepy.StreamListener):
    # This class is listener class, streams in live tweets, process and save onto database

    def on_data(self, raw_data):
        # when there's data coming in
        try:
            data_entry = json.loads(raw_data)  # change raw data into json object
            if not data_entry["retweeted"] and not data_entry["text"].startswith("RT @"):
                # check if data entry is a retweet as we don't want retweets
                remote_tweet_db.save(data_entry)  # save tweet into database
                streamer.harvest_count += 1
            return True

        except BaseException as e:
            print("Error on data: ", str(e))

    def on_error(self, status):
        # twitter api has a case limit and will lock out connection, therefore we stop the program before it can be
        # locked
        if status == 420:
            # return false in case occur case limit
            return False
        print(status)


if __name__ == '__main__':
    # main function
    remote_couch = couchdb.Server('https://admin:answering_railcar@172.26.133.242:6984/')
    remote_couch.resource.session.disable_ssl_verification()

    streamer = TwitterStreamer()

    try:
        remote_tweet_db = remote_couch['tweets_db'] # get tweets database
        db_doc_count = remote_tweet_db.info()['doc_count'] # get total document count of remote database

    except BaseException as e:
        print("Error on connecting to database: ", str(e))
        exit()

    while streamer.harvest_count + db_doc_count < 50000:
        try:
            streamer.stream_tweets() # keep streaming tweets if database document count is lower than 50,000
        except Exception as e:
            print(e)