import requests
import time
import configparser
import sys
import json
import urllib.robotparser

import post_data
import ahto_lib

BASE_USERAGENT = "AhtoHypnohubCrawlerBot/0.0"
USERAGENT = BASE_USERAGENT + " (mailto://weirdusername@techie.com)"

"""
This file is for communicating with Hypnohub and formatting/understanding
Hypnohub's responses.

http://hypnohub.net/help/api
"""

# Make sure we're actually allowed to use these functions.
rp = urllib.robotparser.RobotFileParser()
rp.set_url("http://hypnohub.net/robots.txt")
rp.read()
if (not rp.can_fetch(BASE_USERAGENT, "hypnohub.net/post/index.json")
        or not rp.can_fetch(BASE_USERAGENT, "hypnohub.net/post/index.xml")):
    raise EnvironmentError("robots.txt disallowed us")

cfg = configparser.ConfigParser()
cfg.read('config.cfg')
DELAY = cfg['HTTP Requests'].getfloat('Delay Between Requests')

def get_posts(tags=None, page=None, limit=None):
    """
    Returns an iterable of raw(ish) BeautifulSoup objects. One for each post.

    Remember that this won't be in any particular order unless you ask for
    order:id or something like that.
    """

    time.sleep(DELAY)

    params = {}
    if page is not None:
        params['page'] = page

    if limit is not None:
        params['limit'] = limit

    if tags is not None:
        params['tags'] = tags

    response = requests.get("http://hypnohub.net/post/index.json",
                            params=params, headers={'User-agent': USERAGENT})

    return json.loads(response.text)

def get_simple_posts(*args, **kwargs):
    """ Like get_posts, except the posts are automatically converted into
        SimplePosts.
    """
    return map(post_data.SimplePost, get_posts(*args, **kwargs))
