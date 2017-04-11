import bs4
import requests
import time
import os
import configparser
import pickle
import random
import sys
import post_data

import ahto_lib

"""
This file is for communicating with Hypnohub and formatting/understanding
Hypnohub's responses.

http://hypnohub.net/help/api
"""

# response XML looks like this:
# <posts count="1337" offset="# posts skipped by page">
#   <post
#     id="1337"
#     tags="foo bar_(asdf) baz"
#     score="0"
#     rating="s" # [s]afe, [q]uestionable, [e]xplicite
#     author="foo"
#
#     preview_url="//hypnohub.net//data/preview/d74dced3bddd67137e14d084731bbc0f.jpg"
#     file_url="//hypnohub.net//data/image/d74dced3bddd67137e14d084731bbc0f.jpg"
#     sample_url ???
#
#     status="active" or "deleted" maybe others
#
#     change="0" source="url" created_at="1465946415" creator_id="1337"
#     md5 file_size="775434" is_shown_in_index="1"
#     preview_width preview height
#     actual_preview_width actual_preview_height sample_width
#     sample_height sample_file_size="0" jpeg_url jpeg_width jpeg_height
#     jpeg_file_size="0" width height
#   />
#
#   <post foo bar>
#
#   <post baz qux>
# </posts>

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
    xml = requests.get("http://hypnohub.net/post/index.xml", params=params)
    soup = bs4.BeautifulSoup(xml.text, 'html.parser')

    return soup.find_all('post')

def get_simple_posts(*args, **kwargs):
    """ Like get_posts, except the posts are automatically converted into
        SimplePosts.
    """
    return map(post_data.SimplePost, get_posts(*args, **kwargs))

class PostGetter(object):
    """ An iterator for getting Posts, starting at a given index. """

    def __init__(self, starting_index=0, limit_per_page=None, search_string=""):
        if limit_per_page == None:
            self.limit_per_page = cfg['HTTP Requests'].getint('Limit Per Page')
        else:
            self.limit_per_page = limit_per_page

        self.starting_index = starting_index

        self.search_string = "{search} order:id id:>={index}".format(
            search=search_string, index=starting_index)

        self._current_page = 1
        self.posts = []
        self.highest_id = -1

    def __iter__(self):
        return self

    def get_next_batch(self):
        params = {'page':  self._current_page,
                  'limit': self.limit_per_page}

        if self.search_string:
            params['tags'] = self.search_string

        for post in get_posts(**params):
            post = BSPost(post)
            # TODO: Replace with SimplePost instead. The problem is that later
            # on it asks for post.rating, which SimplePost doesn't (and
            # shouldn't) have.

            if not post.deleted:
                self.posts.append(post)

        self._current_page += 1

    def __next__(self):
        # If we have no locally-stored posts, try 25 times to get new ones. If
        # none are found, give up and StopIteration.
        if len(self.posts) == 0:
            for _ in range(25):
                self.get_next_batch()

                if len(self.posts) > 0:
                    break
            else:
                raise StopIteration

        next_post, self.posts = self.posts[0], self.posts[1:]
        self.highest_id = max(self.highest_id, next_post.id)

        return next_post

    def get_n_good_posts(self, n, sort=True, print_progress=True):
        """ Returns tuple: ([good posts], number of bad posts filtered, number
        of good posts)

        If sort == True, [good posts] will be sorted by post.rating's value,
        desc.
        """

        def progress():
            if print_progress:
                print(
                    '\r{n}: {ng}/{t}'.format(
                        n  = n,
                        ng = n_good_posts,
                        t  = bad_posts_seen + n_good_posts),

                    sep='', end='')

        post_filter = lambda post: post.rating > 0
        post_rater  = lambda post: post.rating

        good_posts = []
        n_good_posts = 0
        bad_posts_seen = 0

        for post in self:
            progress()

            if post_filter(post):
                good_posts.append(post)
                n_good_posts += 1

                # TODO: Debug code; remove later.
                assert n_good_posts == len(good_posts)

                if len(good_posts) >= n:
                    break
            else:
                bad_posts_seen += 1

        progress()
        print()

        if sort:
            good_posts.sort(key=post_rater, reverse=True)

        return good_posts

