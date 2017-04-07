import bs4
import requests
import time
import os
import configparser
import pickle
import random
import sys

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

class SimplePost(object):
    """ A simple way of storing the data of a hypnohub post. It intentionally
    stores the bare minimum, because it's designed to be pickled with about
    50,000 other SimplePosts.
    """

    def __init__(self, data, validate=True):
        """
        data = {
            'id': "1337",
            'tags': 'tag_1 tag_2 tag_3',
            'score': "1337",
            'rating': "s",
            'author': "foo",
            'file_url': "//foo/foo.png",
            'preview_url': "//foo/foo.png",
        }

        Or it can be an object with those as attributes.

        It's also okay, if the post is deleted, to not include 'author' or 'file_url'.
        """
        self._data = dict()

        if hasattr(data, 'author') and isinstance(data.author, str):
            get_data = getattr
        else:
            get_data = lambda d, k: d[k]

        self._data['id']          = get_data(data, 'id')
        self._data['tags']        = get_data(data, 'tags')
        self._data['score']       = get_data(data, 'score')
        self._data['rating']      = get_data(data, 'rating')
        self._data['author']      = get_data(data, 'author')
        self._data['file_url']    = get_data(data, 'file_url')
        self._data['preview_url'] = get_data(data, 'preview_url')

        if validate:
            assert self._data['rating'] in 'sqe'
            int(self._data['id'])
            int(self._data['score'])

    def __getattr__(self, name):
        """ Any invalid attribute reads (to stuff we haven't overwritten) get
        redirected to _data's keys.
        """
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name)

    __getitem__ = __getattr__

    def __repr__(self):
        return ("<SimplePost #{self.id}>").format(**locals())

    def __str__(self):
        return ("#{self.id} +{self.score} by {self.author}").format(
            **locals())

    # These next two are for pickling. Since we use lazy_property's but we
    # don't want to save their cached values to a file, we're only going to
    # tell pickle about the self._data dict and ignore everything else.
    def __getstate__(self):
        return self._data

    def __setstate__(self, data):
        self._data = data

    @ahto_lib.lazy_property
    def tags(self):
        """ Tags are usually in the form "tag_1 tag_2 tag_3 etc" so we'll automatically
        convert them into a list.
        """
        return self['tags'].split(' ')

    @ahto_lib.lazy_property
    def url(self):
        return "http://hypnohub.net/post/show/" + str(self.id) + "/"

    @ahto_lib.lazy_property
    def id(self):
        return int(self['id'])

    @ahto_lib.lazy_property
    def score(self):
        return int(self['score'])

    def has_any(self, tags):
        """ Is tagged with any of the given tags. """
        return any(tag in self.tags for tag in tags)

    def has_all(self, tags):
        """ Is tagged with all of the given tags. """
        return all(tag in self.tags for tag in tags)

    @ahto_lib.lazy_property
    def deleted(self):
        try:
            self._data['file_url']
        except KeyError:
            return True
        else:
            return False

    @ahto_lib.lazy_property
    def preview_url(self):
        # self._data['preview_url'] is in the form:
        #
        # '//hypnohub.net//data/preview/2eea10e9b65a2de8e84ab88dcfd90575.jpg'

        return 'http:' + self._data['preview_url']

    @ahto_lib.lazy_property
    def file_url(self):
        # self._data['file_url'] is in the form:
        #
        # '//hypnohub.net//data/preview/2eea10e9b65a2de8e84ab88dcfd90575.jpg'

        try:
            return 'http:' + self._data['file_url']
        except KeyError:
            return "[deleted]"

class PostCache(object):
    """ A cache of all posts on hypnohub.
    """

    FILENAME = "hypnohub_cache.pickle"

    def __init__(self):
        # example of all_posts = {
        #     1: SimplePost(id=1),
        #     2: SimplePost(id=2),
        #     3: None, # deleted post
        #     ...
        #     999: SimplePost(id=999)
        # }
        if os.path.isfile(self.FILENAME):
            with open(self.FILENAME, 'rb') as cache_file:
                self.all_posts = pickle.load(cache_file)
        else:
            self.all_posts = {}

        self._update_highest_post()

    def get_id(self, id_):
        return self.all_posts[id_]

    def validate_data(self, sample_size=300, print_progress=False):
        """ Make sure there aren't any gaps in the post ID's, except for gaps
        that hypnohub naturally has. (Try searching for "id:8989")

        You can set sample_size to None and it'll check every single post.
        This will obviously take a very long time.
        """
        # [(id, exists), (id, exists), ...]
        ids_and_existance = [(i, (i in self.all_posts))
                             for i in range(1, self.highest_post+1)]

        if sample_size is None or sample_size <= len(missing_ids):
            random.shuffle(ids_and_existance)
            sample = ids_and_existance
        else:
            sample = random.sample(ids_and_existance, sample_size)

        for i, (id_, exists) in enumerate(sample):
            if print_progress:
                print('[', i+1, '/', len(sample), ']', sep='', end=' ')
                print('Checking that ID#', id_, 'has existance:', exists, '...', end=' ')
                sys.stdout.flush()

            assert len(get_posts("id:" + str(id_))) == int(exists), (id_, exists)

            if print_progress:
                print("done.")

    def update_cache(self, print_progress=False):
        new_posts = get_posts(tags="order:id id:>" + str(self.highest_post), limit=100)

        if len(new_posts) == 0:
            return

        if print_progress:
            print("ID#", new_posts[-1]['id'], end=' ')
            print('-', len(new_posts), "posts", end=' ')
            sys.stdout.flush()

        for post in new_posts:
            id_ = int(post['id'])

            if post['status'] == 'deleted':
                self.all_posts[id_] = None
            else:
                self.all_posts[id_] = SimplePost(post)

        if print_progress:
            print('-', len(self.all_posts), 'stored')

        self._update_highest_post()
        self.update_cache(print_progress)

    def _update_highest_post(self):
        if len(self.all_posts) == 0:
            self.highest_post = 0
        else:
            self.highest_post = max(self.all_posts.keys())

    def save_cache(self):
        with open(self.FILENAME, 'wb') as cache_file:
            pickle.dump(self.all_posts, cache_file)

# Create just one instance that everybody can use at the same time.
post_cache = PostCache()

class BSPost(object):
    """ Takes a BeautifulSoup of a Hypnohub post's XML data and gives you some
    convenient methods and properties for getting its info.

    This is a more complex and detailed view of a post than SimplePost. It's
    good for debugging.
    """

    def __init__(self, post_soup):
        self._post_soup = post_soup

    def __getattr__(self, name):
        """ Any invalid attribute reads (to stuff we haven't overwritten) get
        redirected to _post_soup's keys.
        """
        try:
            return self._post_soup[name]
        except KeyError:
            raise AttributeError(name)

    __getitem__ = __getattr__

    def __repr__(self):
        return ("<BSPost #{self.id}>").format(**locals())

    def __str__(self):
        return ("#{self.id} +{self.score} by {self.author}").format(
            **locals())

    @ahto_lib.lazy_property
    def tags(self):
        return self['tags'].split(' ')

    @ahto_lib.lazy_property
    def url(self):
        return "http://hypnohub.net/post/show/" + str(self.id) + "/"

    @ahto_lib.lazy_property
    def id(self):
        return int(self['id'])

    @ahto_lib.lazy_property
    def score(self):
        return int(self['score'])

    def _rate_self(self):
        r = post_rater.rate_post(self, explain=True)
        self._rating, self._rating_explanation = r

    @property
    def rating(self):
        try:
            return self._rating
        except AttributeError:
            self._rate_self()
            return self.rating

    @property
    def rating_explanation(self):
        try:
            return self._rating_explanation
        except AttributeError:
            self._rate_self()
            return self.rating_explanation

    def has_any(self, tags):
        """ Is tagged with any of the given tags. """
        return any(tag in self.tags for tag in tags)

    def has_all(self, tags):
        """ Is tagged with all of the given tags. """
        return all(tag in self.tags for tag in tags)

    @ahto_lib.lazy_property
    def deleted(self):
        try:
            self._post_soup['file_url']
        except KeyError:
            return True
        else:
            return False
        #return 'file_url' not in self._post_soup

    @ahto_lib.lazy_property
    def preview_url(self):
        # self._post_soup['preview_url'] is in the form:
        #
        # '//hypnohub.net//data/preview/2eea10e9b65a2de8e84ab88dcfd90575.jpg'
        #
        # Which is kinda weird and pernicious.

        return 'http:' + self._post_soup['preview_url']

class PostGetter(object):
    """ An iterator for getting Post's, starting at a given index. """

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

