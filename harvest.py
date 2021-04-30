import tweepy
import credential


class MyStreamListener(tweepy.StreamListener):

    def on_status(self, status):
        print(status.created_at)
        print(status.user.location)
        print(status.text)
        print("\n")

    def on_error(self, status_code):
        print(status_code)


auth = tweepy.OAuthHandler(credential.consumer_key, credential.consumer_secret)
auth.set_access_token(credential.access_token, credential.access_token_secret)
api = tweepy.API(auth)

if not api:
    print("Authentication failed")
    exit()

myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)
myStream.filter(track=["covid"])