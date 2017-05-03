import time
import configparser
import sys
import json
import urllib.robotparser
from typing import *
import sys

import requests

import post_data
import ahto_lib

BASE_USERAGENT = "AhtoHypnohubCrawlerBot/0.0"
USERAGENT = BASE_USERAGENT + " (mailto://weirdusername@techie.com)"
DELAY_BETWEEN_REQUESTS_BETWEEN_REQUESTS = 2

"""
This file is for communicating with Hypnohub and formatting/understanding
Hypnohub's responses.

http://hypnohub.net/help/api
"""

# Sending network requests can be slooow! Only do it when we for sure need to.
@ahto_lib.lazy_function
def check_robots_txt():
    rp = urllib.robotparser.RobotFileParser(
            "http://hypnohub.net/robots.txt")

    rp.read()
    time.sleep(DELAY_BETWEEN_REQUESTS)

    if (not rp.can_fetch(BASE_USERAGENT, "hypnohub.net/post/index.json")
            or not rp.can_fetch(BASE_USERAGENT, "hypnohub.net/post/index.xml")):
        raise EnvironmentError("robots.txt disallowed us!")

def get_posts(tags=None, page=None, limit=None):
    """
    Returns an iterable of raw parsed-JSON objects. One for each post.

    Remember that this won't be in any particular order unless you ask for
    order:id or something like that.
    """
    check_robots_txt()

    params = {}
    if page is not None:
        params['page'] = page

    if limit is not None:
        params['limit'] = limit

    if tags is not None:
        params['tags'] = tags

    response = requests.get("http://hypnohub.net/post/index.json",
                            params=params, headers={'User-agent': USERAGENT})

    time.sleep(DELAY_BETWEEN_REQUESTS)

    return json.loads(response.text)

def get_simple_posts(*args, **kwargs):
    """ Like get_posts, except the posts are automatically converted into
    SimplePosts.
    """
    return map(post_data.SimplePost, get_posts(*args, **kwargs))

def get_vote_data(user, vote_level) -> Set[int]:
    """
    Vote levels:
    3:    Favorite
    2:    "Great"
    1:    "Good"
    """

    max_post = 0
    post_ids = set()
    while True:
        posts = get_posts(
            f'vote:{vote_level}:{user} order:id id:>{max_post}')
        new_post_ids = {i['id'] for i in posts}

        if __debug__ and len(new_post_ids) != 0:
            assert len(new_post_ids & post_ids) < len(new_post_ids)

        post_ids |= new_post_ids

        if max_post == max(*post_ids):
            break

        max_post = max(*post_ids)

    return post_ids
