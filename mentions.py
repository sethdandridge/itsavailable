# -*- coding: utf-8 -*-
import string
import socket
import logging

import tweepy
import pythonwhois

VALID_DOMAIN_CHARS = set(string.ascii_letters + string.digits + '-')

def is_available(domain):
    try:
        whois = pythonwhois.get_whois(domain + '.com')
    except (UnicodeError, socket.error, pythonwhois.shared.WhoisException) as msg:
        logging.info(f'Availability check error: {msg}')
    else:
        if "No match" in whois['raw'][0]:
            return True
    return False

class MentionListener(tweepy.StreamListener):

    def __init__(self, api):
        self.api = api

    def on_status(self, status):
    
        if status.entities['urls']:
            logging.info(f"{status.text} contains a URL")
            return

        request_string = '-'.join([t for t in status.text.split() if '@' not in t])

        if len(request_string) > 63:
            response = f'"{request_string[:63]}..." is too long. domains must be less than 64 characters'
        elif set(request_string) - VALID_DOMAIN_CHARS:
            response = f'"{request_string}" can\'t be a domain. letters, numbers, and dashes only'
        elif not is_available(request_string):
            response = f'{request_string}․com is not available'
        else:
            response = f'{request_string}․com is available'

        tweet_text = f"@{status.user.screen_name} {response}"
        self.api.update_status(tweet_text, in_reply_to_status_id=status.id)

        logging.info(f"mention: tweeting {tweet_text}")

def run(api):
    logging.info("mention: thread starting")
    while True:
        try:
            stream = tweepy.Stream(auth=api.auth, listener=MentionListener(api))
            stream.filter(track=['@itsavailable'])
        except Exception as msg:
            logging.error(f"mention: restarting {msg}")
            continue
