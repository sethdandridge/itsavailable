


# @itsavailable
Bot that tweets unregistered .com domains

## Overview
Gets eligible domains from 3 sources:
1. Most-visited English-language Wikipedia pages in the past hour
2. Tweets from @NYT_first_said
3. @ mentions sent directly to the bot

## Requirements
Python3.6+

## Install
- Create environmental variables with your Twitter API credentials
- pip install -r requirements.txt
- python3.6 itsavailable.py

## To-do, limitations
- The domain availability logic can be tricked if the words "No match" are anywhere in the WHOIS record
- Wikipedia hashtags are sourced from the most-visited articles which contain a link to article being tweeted and are not always relevant
- No logic for handling Twitter streaming API failures
- God forbid another reply bot ever sends an @ mention and causes an infinite loop
