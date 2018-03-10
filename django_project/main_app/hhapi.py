import time
import json
import urllib.robotparser

import requests

BASE_USERAGENT = "AhtoHypnohubCrawlerBot/0.0"
USERAGENT = BASE_USERAGENT + " (mailto://weirdusername@techie.com)"

# Try to be polite to the server
# A request is heavy if it gets more than 100 results back. Everything else
# (including robots.txt) is a light request.
DELAY_BETWEEN_LIGHT_REQUESTS =   1
DELAY_BETWEEN_HEAVY_REQUESTS =   5
MAX_POSTS_PER_REQUEST        = 500

"""
This file is for communicating with the Hypnohub API (hence the name) and
processing Hypnohub's responses.

http://hypnohub.net/help/api
"""

class RequestDelayer:
    def __init__(self):
        self.no_requests_until = time.time()

    def _request(self, no_requests_for):
        if self.no_requests_until > time.time():
            time.sleep(self.no_requests_until - time.time())

        self.no_requests_until = time.time() + no_requests_for

    def light_request(self):
        self._request(DELAY_BETWEEN_LIGHT_REQUESTS)

    def heavy_request(self):
        self._request(DELAY_BETWEEN_HEAVY_REQUESTS)

class HypnohubAPIRequester:
    def __init__(self):
        self.request_delayer = RequestDelayer()
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

        self.request_delayer.light_request()

        robots_allowed = rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.json")
        robots_allowed = robots_allowed or rp.can_fetch(
            BASE_USERAGENT,
            "hypnohub.net/post/index.xml")

        if not robots_allowed:
            raise EnvironmentError("robots.txt disallowed us!")

    def process_post(self, post):
        """
        Given a parsed JSON post from HypnoHub, process the attributes in such
        a way that they're more usable and understandable.

        For example, add 'http:' to the left side of URL's. And, if 'parent'
        isn't sent, set it to None (which will become NULL once it enters the
        database).
        """

        post['file_url']    = 'http:' + post['file_url']
        post['sample_url']  = 'http:' + post['sample_url']
        post['preview_url'] = 'http:' + post['preview_url']

        if 'parent' not in post:
            post['parent'] = None

        return post

    def get_posts(self, tags=None, page=None, limit=MAX_POSTS_PER_REQUEST):
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
        if limit > MAX_POSTS_PER_REQUEST:
            raise ValueError("limit can't be > MAX_POSTS_PER_REQUEST")

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

        response = json.loads(response.text)

        if len(response) > 100:
            self.request_delayer.heavy_request()
        else:
            self.request_delayer.light_request()

        return map(self.process_post, response)

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
        return next(self.get_posts('order:id_desc', limit=1))['id']

    def print_while_fetching(self, tags='', printer=None):
        """
        This function is designed for crawling through enormous numbers of
        HypnoHub posts, and printing your progress as you go. Specifically,
        it's designed to crawl through all of HypnoHub, all in one go.

        Returns an iterator of parsed-JSON posts, just like get_posts().

        You can set tags to whatever you want, as long as you don't change the
        order.

        printer
            Args: (highest_id_seen, highest_id_in_hypnohub)

            Will get called every time we complete a new HTTP request. The idea
            is you can use it to update a loading bar, or print to the screen.
        """
        tags += " order:id"
        current_page    = 1
        highest_id_seen = None

        highest_id = self.get_highest_id()

        while True:
            new_posts = list(self.get_posts(tags, current_page))
            current_page += 1

            if len(new_posts) == 0:
                break

            highest_id_seen = new_posts[-1]['id']

            if printer is not None:
                printer(highest_id_seen, highest_id)

            yield from new_posts
