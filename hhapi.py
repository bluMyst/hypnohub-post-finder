import time
import json
import urllib.robotparser

import requests

import post_data
import ahto_lib

BASE_USERAGENT = "AhtoHypnohubCrawlerBot/0.0"
USERAGENT = BASE_USERAGENT + " (mailto://weirdusername@techie.com)"
DELAY_BETWEEN_REQUESTS = 2

"""
This file is for communicating with the Hypnohub API (hence the name) and
processing Hypnohub's responses.

http://hypnohub.net/help/api
"""

class HypnohubAPIRequester(object):
    def __init__(self):
        self.check_robots_txt()

    def check_robots_txt():
        """
        Make sure our useragent is allowed to access the two URL's it might
        request.

        Last I checked (2017-11-16), HypnoHub's robots.txt was completely blank.
        """
        rp = urllib.robotparser.RobotFileParser(
            "http://hypnohub.net/robots.txt")

        rp.read()

        # I'm pretty sure .read() is blocking and this is just here in case we
        # make other requests. So we don't spam them too fast.
        time.sleep(DELAY_BETWEEN_REQUESTS)

        robots_allowed = rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.json")
        robots_allowed = robots_allowed or rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.xml")

        if not robots_allowed:
            raise EnvironmentError("robots.txt disallowed us!")

    def get_posts(self, tags=None, page=None, limit=None):
        """
        Returns an iterable of raw parsed-JSON objects. One for each post.

        Remember that this won't be in any particular order unless you ask for
        order:id or something like that. It works exactly like the search system on
        the actual website.
        """
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
    """
    Like get_posts, except the posts are automatically converted into
    SimplePosts.
    """
    return map(post_data.SimplePost, get_posts(*args, **kwargs))


def get_vote_data(user, vote_level):
    """
    Vote levels:
    3:    Favorite
    2:    "Great"
    1:    "Good"

    These levels are inherent to HypnoHub. They're not anything that I made up.

    Returns a set of post ID's (as int).
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
