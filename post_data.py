import os
import pickle
import sys
import string
import bz2

import hhapi

"""
Classes for storing data on Hypnohub posts.
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
#     md5="d74dced3bddd67137e14d084731bbc0f"
#     file_url   = "//hypnohub.net//data/image/[md5 goes here].jpg"
#     preview_url= "//hypnohub.net//data/preview/[md5 goes here].jpg"
#     sample_url = "//hypnohub.net//data/sample/[md5 goes here].jpg"
#     jpeg_url=always same as file_url
#     Sometimes URLs end in .png instead.
#
#     status="active" or "deleted" maybe others
#
#     change="0" source="url" created_at="1465946415" creator_id="1337"
#     md5 file_size="775434" is_shown_in_index="1"
#     preview_width preview height
#     actual_preview_width actual_preview_height sample_width
#     sample_height sample_file_size="0" jpeg_width jpeg_height
#     jpeg_file_size="0" width height
#   />
#
#   <post foo bar>
#
#   <post baz qux>
# </posts>


class SimplePost(object):
    """
    A simple way of storing the data of a Hypnohub post. It intentionally
    stores the bare minimum, because it's designed to be pickled with about
    50,000 other SimplePosts.
    """

    FIELDS_USED = {'id', 'rating', 'author', 'score', 'tags', 'md5',
                   'file_url', 'preview_url', 'sample_url', 'jpeg_url'}

    FIELDS_STORED = FIELDS_USED - {'jpeg_url'}

    IMMUTABLE_FIELDS_STORED = FIELDS_STORED - {'score', 'tags', 'rating'}

    def __init__(self, data):
        """
        Example "data": {
            'id': 1337, # or "1337", but Hypnohub gives int's.

            # These are optional, but a post without them will be assumed to be
            # deleted.
            'score': "1337", # or 1337, but Hypnohub gives str's.
            'rating': "s",
            'tags': 'tag_1 tag_2 tag_3',
            'author': "foo",
            'md5': "6c9b5fe35b3f74fd444f4b1e969eb974",
            'file_url': '//hypnohub.net//data/image/[snip].jpg',
            'preview_url', 'sample_url', 'jpeg_url'
        }

        This class is designed so that you can give it the JSON object from an
        HTTP request to Hypnohub and it can parse all of that data and store it
        in the smallest space possible.
        """
        self.deleted = False

        self.id = int(data['id'])

        if any((i not in data) for i in self.FIELDS_USED):
            self.deleted = True
            return

        self.score  = int(data['score'])
        self.tags   = set(data['tags'].split(' '))
        self.author = data['author']

        self.rating = data['rating']
        assert self.rating is None or self.rating in 'sqe'

        self.md5 = data['md5']
        assert all((i in string.hexdigits) for i in self.md5)

        assert data['file_url'] == data['jpeg_url']
        self.file_url    = data['file_url']
        self.preview_url = data['preview_url']
        self.sample_url  = data['sample_url']

    def __eq__(self, other):
        if self.deleted != other.deleted:
            return False
        elif self.deleted:
            return True

        for attr in self.IMMUTABLE_FIELDS_STORED:
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    def __repr__(self):
        if self.deleted:
            return f"<SimplePost #{self.id} DELETED>"
        else:
            return f"<SimplePost #{self.id}>"

    def __str__(self):
        str_ = f"#{self.id}"

        if self.deleted:
            str_ += "[d]"

        if hasattr(self, 'score'):
            str_ += f" +{self.score}"
        else:
            str_ += " [no score]"

        if hasattr(self, 'author'):
            str_ += f" by {self.author}"
        else:
            str_ += " [no author]"

        return str_

    @property
    def page_url(self):
        return f"http://hypnohub.net/post/show/{self.id}/"


class Dataset(object):
    """ Tracks the posts that the user has liked and disliked. Stores them in a
    file for later use. Also keeps a cache of all Hypnohub posts on the site.

    self.good = [good_id, good_id, ...]
    self.bad = [bad_id, bad_id, ...]

    self.cache = {
        post_id: SimplePost(post_id),
        post_id: SimplePost(post_id),
        ...
    }
    """
    DATASET = "dataset.pickle.bz2"
    CACHE   = "cache.pickle.bz2"

    def __init__(self):
        if os.path.isfile(self.DATASET):
            with bz2.open(self.DATASET, 'rb') as f:
                raw_dataset = pickle.load(f)

            self.good = raw_dataset['good']
            self.bad = raw_dataset['bad']
        else:
            self.good = set()
            self.bad = set()

        if os.path.isfile(self.CACHE):
            with bz2.open(self.CACHE, 'rb') as f:
                self.cache = pickle.load(f)
        else:
            self.cache = {}

    @property
    def cache_empty(self):
        return len(self.cache) == 0

    def save(self):
        """ Save dataset back to pickle file. """
        with bz2.open(self.DATASET, 'wb') as f:
            pickle.dump({'good': self.good, 'bad': self.bad}, f)

        with bz2.open(self.CACHE, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_highest_post(self):
        if len(self.cache) == 0:
            return 0
        else:
            return max(self.cache.keys())

    def get_id(self, id_):
        """ Get a SimplePost from the cache by post id.

        Returns a blank, deleted SimplePost if the id wasn't found.
        """
        try:
            return SimplePost(self.cache[id_])
        except KeyError:
            return SimplePost({'id': id_})

    def get_good(self):
        """ Get all good posts. Not ID's like self.good, but actual SimplePost
        objects.
        """
        return map(self.get_id, self.good)

    def get_bad(self):
        """ Get all bad posts. Not ID's like self.bad, but actual SimplePost
        objects.
        """
        return map(self.get_id, self.bad)

    def get_all(self):
        """ Get all posts, in SimplePost form. """
        return map(SimplePost, self.cache.values())

    def update_cache(self, print_progress=True):
        new_posts = list(hhapi.get_posts(
            tags="order:id id:>" + str(self.get_highest_post()),
            limit=100))

        if len(new_posts) == 0:
            return

        if print_progress:
            print("ID#", new_posts[-1]['id'], end=' ')
            print('-', len(new_posts), "posts", end=' ')
            sys.stdout.flush()

        for post in new_posts:
            spost = SimplePost(post)

            if not spost.deleted:
                self.cache[spost.id] = post

        if print_progress:
            print('-', len(self.cache), 'stored')

        self.update_cache(print_progress)
