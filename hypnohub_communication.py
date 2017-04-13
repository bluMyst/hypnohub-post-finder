import requests
import time
import os
import configparser
import pickle
import random
import sys
import post_data
import json

import ahto_lib

"""
This file is for communicating with Hypnohub and formatting/understanding
Hypnohub's responses.

http://hypnohub.net/help/api
"""

cfg = configparser.ConfigParser()
cfg.read('config.cfg')

def get_posts(tags= None, page=None, limit=None):
    """
    Returns an iterable of raw(ish) BeautifulSoup objects. One for each post.

    Remember that this won't be in any particular order unless you ask for
    order:id or something like that.
    """

    time.sleep(cfg['HTTP Requests'].getfloat('Delay Between Requests'))

    params = {}
    if page is not None:
        params['page'] = page

    if limit is not None:
        params['limit'] = limit

    if tags is not None:
        params['tags'] = tags

    # lxml won't install on my system so I have to use an html parser on
    # xml. Trust me: it's better than the hack I was using before.
    response = requests.get("http://hypnohub.net/post/index.json", params=params)
    return json.loads(response.text)

def get_simple_posts(*args, **kwargs):
    """ Like get_posts, except the posts are automatically converted into
        SimplePosts.
    """
    return map(post_data.SimplePost, get_posts(*args, **kwargs))
