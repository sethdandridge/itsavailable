# -*- coding: utf-8 -*-
import string
import socket
import logging

import tweepy
import pythonwhois

NYT_TWITTER_ID = 838207103852396544

def is_available(domain):
    try:
        whois = pythonwhois.get_whois(domain + '.com')
    except (UnicodeError, socket.error, pythonwhois.shared.WhoisException) as msg:
        logging.error(f'nyt: availability check error: {msg}')
    else:
        if "No match" in whois['raw'][0]:
            return True
    return False

class NYTListener(tweepy.StreamListener):

    def __init__(self, api):
        self.api = api
        self.valid_domain_chars = set(string.ascii_letters + string.digits + '-')

    def on_status(self, status):
        if status.user.id != NYT_TWITTER_ID:
            return 
            logging.info(f'nyt: {status.text} (not from nyt account)')
        elif set(status.text) - self.valid_domain_chars:
            logging.info(f'nyt: {status.text} contains invalid characters')
        elif len(status.text) > 63:
            logging.info(f'nyt: {status.text} is too long')
        elif not is_available(status.text):
            logging.info(f'nyt: {status.text}.com is not available')
        else: 
            tweet_text = f"@NYT_first_said {status.text}․com" #special dot 
            try: 
                self.api.update_status(tweet_text, in_reply_to_status_id=status.id)
            except Exception as msg:
                logging.info(f'nyt: error tweeting {tweet_text}: {msg}')
            else:
                logging.info(f"nyt: tweeting {tweet_text}")

def run(api):
    logging.info("nyt: thread starting")
    while True:
        try:
            stream = tweepy.Stream(auth=api.auth, listener=NYTListener(api))
            stream.filter(follow=[str(NYT_TWITTER_ID)])
        except Exception as msg:
            logging.error(f"nyt: restarting {msg}")
            continue
