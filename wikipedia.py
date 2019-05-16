# -*- coding: utf-8 -*-
import logging
import time
import random
import socket
import pythonwhois
import urllib
import re
import string
import unicodedata
from bs4 import BeautifulSoup
import requests
import gzip
from collections import Counter
import psycopg2
from psycopg2.extras import execute_values

def tweet(api, domain, entry, count, hashtags):
    #special case because twitter doesn't like en dashes
    resource = entry.replace("–", "%E2%80%93")
    tweet_text = f"{domain}․com https://en.wikipedia.org/wiki/{resource}{hashtags}" #special . in .com
    try: 
        status = api.update_status(tweet_text)
    except Exception as e:
        logging.error(f'error tweeting {tweet_text} ({count})')
        logging.error(e)
    else:
        logging.info(f'successfully tweeted {tweet_text} ({count})')

def is_title_valid(title):
    if (title == 'Main_Page' or
            title == '-' or
            '–' in title or
            '—' in title or
            title.startswith('List') or
            title.startswith('File:') or
            title.startswith('Special:') or
            title.startswith('Talk:') or
            title.startswith('Help:') or
            title.startswith('Category:') or
            title.startswith('Wikipedia:') or
            title.startswith('Portal:') or
            title.startswith('Template:') or
            title.startswith('File_talk:') or
            title.startswith('User:') or
            title[:4].isdigit() or
            len(title) >= 42 or
            len(title.split('_')) > 4 or
            'of' in title.split('_')
        ):
        return False

    return True

def is_available(domain):
    if len(domain) > 63:
        return False
    try:
        whois = pythonwhois.get_whois(domain + '.com')
    except UnicodeError:
        return False
    except (socket.error, pythonwhois.shared.WhoisException) as msg:
        logging.info('whois error')
        time.sleep(15)
        return False
    else:
        if "No match" in whois['raw'][0]:
            return True
        else:
            return False

def asciify_title(title):
    if set(title).difference(set(string.printable)):
        asciified = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
        if asciified:
            asciified = asciified.decode('utf-8')
            if len(asciified) == len(title):
                return asciified
            else:
                return False
        else:
            return False
    else:
        return title

def strip_disambiguation(title):
    m = re.search(r"(.*)\([^()]+\)$", title)
    if m:
        return m.groups(0)[0].strip('_')
    else:
        return title

def depunctuate(title):
    title = title.replace('&', 'and')
    return ''.join([c for c in title if c in string.ascii_letters + string.digits + '-' + '_'])

def get_last_hour_pageview_url():
    index_url = "https://dumps.wikimedia.org/other/pageviews/"
    r = requests.get(index_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    for link in soup.findAll('a'):
        if 'readme' not in link.get('href'):
            year_url = index_url + link.get('href')

    r = requests.get(year_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    for link in soup.findAll('a'):
        month_url = year_url + link.get('href')

    r = requests.get(month_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    for link in soup.findAll('a'):
        if 'pageviews' in link.get('href'):
            most_recent_log_url = month_url + link.get('href')

    return most_recent_log_url

def download_logfile(most_recent_log_url):
    logging.info(f'downloading {most_recent_log_url}')
    r = requests.get(most_recent_log_url)
    logfile = gzip.decompress(r.content).decode('utf-8')

    logging.info(f'processing {most_recent_log_url}')
    c = Counter()
    for line in logfile.splitlines():
        if line.startswith('en ') or line.startswith('en.m '):
            try:
                domain_code, page_title, count_views, _ = line.split()
                c[page_title] += int(count_views)
            except ValueError:
                continue
    return c

def mark_as_unavailable(title):
    sql = (
        "INSERT INTO page (title, is_availabity_checked) "
        "VALUES (%s, TRUE) "
        "ON CONFLICT (title) DO UPDATE "
        " SET is_availabity_checked = TRUE; "
    )
    with db.cursor() as cursor:
        cursor.execute(sql, (title,))

def mark_as_tweeted(title):
    sql = (
        "INSERT INTO page (title, is_tweeted) "
        "VALUES (%s, TRUE) "
        "ON CONFLICT (title) DO UPDATE "
        " SET is_tweeted = TRUE; "
    )
    with db.cursor() as cursor:
        cursor.execute(sql, (title,))

def get_json(title):
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php",
                params={
                    'action': 'query',
                    'format': 'json',
                    'prop': 'extracts|linkshere|categories',
                    'explaintext': '1',
                    'exchars': '350',
                    'exlimit': '1',
                    'redirects': '1',
                    'cllimit': '500',
                    'lhlimit': '500',
                    'titles' : title,
                }
            )
    except:
        return None
    try:
        json = r.json()
        return next(iter(json['query']['pages'].values()))
    except:
        return None

def is_person_or_team(json):
    forbidden_words = [
        'people',
        'team',
        'births',
        'deaths',
        'ships',
        'mma',
        'ufc',
        'days of the year'
    ]
    for category in json.get('categories', []):
        for forbidden_word in forbidden_words:
            if forbidden_word in category['title'].lower():
                return True
    if 'team' in json.get('extract', ''):
        return True
    return False

def get_hashtags(json, title, pageviews):
    links = []
    for link in json.get('linkshere', []):
        link['views'] = pageviews.get(link['title'], 0)
        links.append(link)
    hashtags = ''
    lowercase_hashtags = set()
    for link in sorted(links, key=lambda x: x['views'], reverse=True):
        linktitle = link['title'].replace(' ', '')
        if set(linktitle).difference(set(string.ascii_letters)):
            continue
        elif linktitle.lower().startswith("list"):
            continue
        elif len(hashtags + f" #{linktitle}") > 72:
            return hashtags
        else:
            if linktitle.lower() in lowercase_hashtags:
                continue
            else:
                hashtags += f" #{linktitle}"
                lowercase_hashtags.add(linktitle.lower())
    return hashtags

def is_tweeted_or_unavailable(title):
    sql = (
        "SELECT * FROM page "
        "WHERE title = %s "
        " AND (is_tweeted = TRUE "
        " OR is_availabity_checked = TRUE) "
        "LIMIT 1; "
    )
    with db.cursor() as cursor:
        cursor.execute(sql, (title,))
        if cursor.fetchone():
            return True
        else:
            return False

db = psycopg2.connect("dbname=itsavailable")
db.autocommit = True

def run(api):
    logging.info("Wikipedia thread started")

    while True:
        most_recent_log_url = get_last_hour_pageview_url()
        pageviews = download_logfile(most_recent_log_url)
        for title, count in pageviews.most_common():
            if is_tweeted_or_unavailable(title):
                # Title has already been tweeted or marked as bad
                continue

            if not is_title_valid(title):
                # Title is not a good article name
                mark_as_unavailable(title)
                continue

            _title = asciify_title(title)
            if not _title:
                # Title is not ascifiiable
                mark_as_unavailable(title)
                continue

            json = get_json(title)
            if json is None:
                continue

            if is_person_or_team(json):
                # Title is a person, team, or otherwise uninteresting
                mark_as_unavailable(title)
                continue

            hashtags = get_hashtags(json, title, pageviews)

            _title = strip_disambiguation(_title)
            _title = depunctuate(_title)
            _title_nospace = _title.replace('_', '').replace('-', '')
            _title_hyphens = _title.replace('_', '-')
            _title_hyphens = _title_hyphens.replace('--', '-')

            if is_available(_title_nospace):
                mark_as_tweeted(title)
                tweet(api, _title_nospace, title, count, hashtags)
                break
            elif is_available(_title_hyphens):
                mark_as_tweeted(title)
                tweet(api, _title_hyphens, title, count, hashtags)
                break
            else:
                mark_as_unavailable(title)
        next_run = random.randint(60*60*2, 60*60*3) 
        logging.info(f'wikipedia thread starting over in {int(next_run/60)} minutes')
        time.sleep(next_run) 
