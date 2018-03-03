import time
import json
import urllib.robotparser

import requests

BASE_USERAGENT = "AhtoHypnohubCrawlerBot/0.0"
USERAGENT = BASE_USERAGENT + " (mailto://weirdusername@techie.com)"

# Be very polite to the server.
DELAY_BETWEEN_REQUESTS = 2

"""
This file is for communicating with the Hypnohub API (hence the name) and
processing Hypnohub's responses.

http://hypnohub.net/help/api
"""

class HypnohubAPIRequester(object):
    def __init__(self):
        self.check_robots_txt()

    def check_robots_txt(self):
        """
        Make sure our useragent is allowed to access the two URL's it might
        request.

        Last I checked (2018-03-01), HypnoHub's robots.txt was completely
        blank.
        """
        rp = urllib.robotparser.RobotFileParser(
            "http://hypnohub.net/robots.txt")

        rp.read()

        time.sleep(DELAY_BETWEEN_REQUESTS)

        robots_allowed = rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.json")
        robots_allowed = robots_allowed or rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.xml")

        if not robots_allowed:
            raise EnvironmentError("robots.txt disallowed us!")

    def get_posts(self, tags=None, page=None, limit=200):
        """
        Returns a list of dicts, parsed straight from the JSON. One for each
        post.

        You can set limit to 'None' to not send a limit. If you do this,
        Hypnohub will probably end up sending you 30 posts at a time.

        Apparently you can set 'limit' to absurdly high numbers (I've tried up
        to 1000) and Hypnohub will happily churn along and give you the data
        you want. With this great power comes great responsibility: Don't
        overtax the servers! It's probably better to ask for little chunks of
        data at a time. Like about 200 posts at a time?

        Remember that this will be in descending order, by id unless you ask
        for order:id or something like that. It works exactly like the
        search system on the actual website.

        Also remember that 'tags' actually takes a string of search terms, just
        like on the actual website.
        """
        params = {}
        if page is not None:
            params['page'] = page

        if limit is not None:
            params['limit'] = limit

        if tags is not None:
            params['tags'] = tags

        response = requests.get(
            "http://hypnohub.net/post/index.json",
            params=params,
            headers={'User-agent': USERAGENT}
        )

        time.sleep(DELAY_BETWEEN_REQUESTS)

        return json.loads(response.text)

    def get_all_matching_posts(self, tags=None):
        """
        Like get_posts but loops through every page until there's nothing left.

        This is an iterable that yields new posts as-needed, one at a time.
        They're retrieved in chunks of 100, though.

        Be careful with this method! Don't just load all of HypnoHub into RAM
        at once. This function is lazy for a reason.
        """
        current_page = 1
        posts = []

        while True:
            new_posts = self.get_posts(tags, current_page)

            if len(new_posts) == 0:
                break

            yield from new_posts
            current_page += 1

    def get_highest_id(self):
        # id_desc is the default order but I'm setting it just to be safe.
        return self.get_posts('order:id_desc', limit=1)[0]['id']

    def get_complete_post_list(self):
        """
        yields (new_posts, highest_id_seen, highest_id_in_hypnohub)

        new_posts is a list of posts, usually 100 of them

        The last two args are for progress bars and such.

        It's completely fine to use get_all_matching_posts for the same purpose
        as this function. The only difference is this one yields values in a
        different way, and won't let you set a 'tags' value.
        """
        current_page    = 1
        highest_id_seen = None

        highest_id = self.get_highest_id()

        while True:
            new_posts = self.get_posts(tags="order:id", page=current_page)
            current_page += 1

            if len(new_posts) == 0:
                break

            highest_id_seen = new_posts[-1]['id']

            yield new_posts, highest_id_seen, highest_id
