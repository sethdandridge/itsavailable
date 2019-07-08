import os
import threading
import logging

import tweepy

import wikipedia
import mentions
import nyt

if __name__ == "__main__":
    # Format logger
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.INFO)

    # Create twitter API
    CONSUMER_KEY = os.environ['ITSAVAILABLE_CONSUMER_KEY']
    CONSUMER_SECRET = os.environ['ITSAVAILABLE_CONSUMER_SECRET']
    TOKEN_KEY = os.environ['ITSAVAILABLE_TOKEN_KEY']
    TOKEN_SECRET = os.environ['ITSAVAILABLE_TOKEN_SECRET']
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(TOKEN_KEY, TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    # Start all the threads
    wikipedia_thread = threading.Thread(target=wikipedia.run, args=(api,))
    wikipedia_thread.start()
    nyt_thread = threading.Thread(target=nyt.run, args=(api,))
    nyt_thread.start()
    mentions_thread = threading.Thread(target=mentions.run, args=(api,))
    mentions_thread.start()
