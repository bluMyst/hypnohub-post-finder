import os
import pickle
import sys
import random

import hypnohub_communication as hhcom

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

class SimplePost(object):
    """ A simple way of storing the data of a hypnohub post. It intentionally
    stores the bare minimum, because it's designed to be pickled with about
    50,000 other SimplePosts.
    """

    def __init__(self, data, validate=True):
        """
        data = {
            'id': "1337",

            # These are optional, but a post without them will be assumed to be
            # deleted.
            'score': "1337",
            'rating': "s",
            'preview_url': "//foo/foo.png",
            'tags': 'tag_1 tag_2 tag_3',
            'author': "foo",
            'file_url': "//foo/foo.png",
        }

        Or it can be an object with those as attributes, or even a
        BeautifulSoup of Hypnohub's response XML!

        It's also okay, if the post is deleted, to not include 'author' or
        'file_url'.
        """
        self._data = dict()
        self.deleted = False

        if 'id' in data:
            get_data = lambda k: data[k]
        elif hasattr(data, 'id'):
            get_data = lambda k: getattr(data, k)
        else:
            raise ValueError("data has no id.")

        def safe_get_data(key, postprocessing=lambda x: x, default=None):
            try:
                data = get_data(key)
            except (AttributeError, KeyError):
                self.deleted = True
                return default

            return postprocessing(data)

        self.id          = int(get_data('id'))
        self.rating      = safe_get_data('rating')
        self.author      = safe_get_data('author')
        self.score       = safe_get_data('score',       int)
        self.preview_url = safe_get_data('preview_url', lambda x: 'http:' + x)
        self.file_url    = safe_get_data('file_url',    lambda x: 'http:' + x)
        self.tags        = safe_get_data('tags',        lambda x: x.split(' '))

        self.page_url = 'http://hypnohub.net/post/show/' + str(self.id) + '/'

        assert self.rating in 'sqe'

    def __repr__(self):
        return ("<SimplePost #{self.id}>").format(**locals())

    def __str__(self):
        return ("#{self.id} +{self.score} by {self.author}").format(
            **locals())

class Dataset(object):
    """ Tracks the posts that the user has liked and disliked. Stores them in a
        file for later use. Also keeps a cache of all Hypnohub posts on the
        site.

        self.good = [good_id, good_id, ...]
        self.bad = [bad_id, bad_id, ...]

        self.cache = {
            post_id: SimplePost(post_id),
            post_id: SimplePost(post_id),
            ...
        }
    """
    DATASET = "dataset.pickle"
    CACHE   = "cache.pickle"

    def __init__(self):
        if os.path.isfile(self.DATASET):
            with open(self.DATASET, 'rb') as f:
                raw_dataset = pickle.load(f)

            self.good = raw_dataset['good']
            self.bad = raw_dataset['bad']
        else:
            self.good = set()
            self.bad = set()

        if os.path.isfile(self.CACHE):
            with open(self.CACHE, 'rb') as f:
                self.cache = pickle.load(f)
        else:
            self.cache = {}

    def save(self):
        """ Save dataset back to pickle file. """
        with open(self.DATASET, 'wb') as f:
            pickle.dump({'good': self.good, 'bad': self.bad}, f)

        with open(self.CACHE, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_highest_post(self):
        if len(self.cache) == 0:
            return 0
        else:
            return max(self.cache.keys())

    def get_id(self, id_):
        """ Get a post from the cache by post id.

            Returns None if the post doesn't exist.
        """
        try:
            return self.cache[id_]
        except KeyError:
            return None

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

    def update_cache(self, print_progress=True):
        new_posts = list(hhcom.get_simple_posts(
            tags="order:id id:>" + str(self.get_highest_post()),
            limit=100))

        if len(new_posts) == 0:
            return

        if print_progress:
            print("ID#", new_posts[-1].id, end=' ')
            print('-', len(new_posts), "posts", end=' ')
            sys.stdout.flush()

        for post in new_posts:
            if not post.deleted:
                self.cache[post.id] = post

        if print_progress:
            print('-', len(self.cache), 'stored')

        self.update_cache(print_progress)

# There should only ever be one of these, since the data is pickled.
dataset = Dataset()

def validate_cache(sample_size=300, print_progress=True):
    """ Make sure there aren't any gaps in the post ID's, except for gaps
        that hypnohub naturally has. (Try searching for "id:8989")

        You can set sample_size to None and it'll check every single post.
        This will obviously take an absurd length of time.
    """
    # TODO:
    # I know what you're thinking: It doesn't have to be this slow! You can
    # just do searches like one of these:
    #
    # id:>=100 id:<=200
    # ~id:1337 ~id:6969 ~id:42
    #
    # Well it turns out that the former won't work because Hypnohub only
    # follows the second (last?) "id:" statement, and the latter won't work
    # because you can't use OR on a special operator like that. But there
    # /is/ a workaround! Remember how HypnoHub will only give us a maximum
    # of 100 posts at a time? Well all we have to do is ask for 100 posts
    # and...
    #
    # order:id_desc id:<=300

    # [(id, exists), (id, exists), ...]
    highest_post = dataset.get_highest_post()

    ids_and_existance = [
        (i, (i in dataset.cache)) for i in range(1, highest_post+1)]

    if sample_size is None or sample_size >= len(ids_and_existance):
        random.shuffle(ids_and_existance)
        sample = ids_and_existance
        sample_size = len(sample)
    else:
        sample = random.sample(ids_and_existance, sample_size)

    for i, (id_, exists) in enumerate(sample):
        if print_progress:
            print('[', i+1, '/', sample_size, ']', sep='', end=' ')
            print('Checking that ID#', id_, 'has existance:', exists, '...',
                  end=' ')
            sys.stdout.flush()

        post_data = list(hhcom.get_simple_posts("id:" + str(id_)))

        if len(post_data) == 0:
            deleted = True
        elif len(post_data) == 1:
            deleted = post_data[0].deleted
        else:
            assert False, ("Something went wrong when trying to communicate "
                           "with Hypnohub and it's probably their fault.")

        if deleted == exists:
            if exists:
                raise Exception("Post #" + str(id_) + " doesn't exist but "
                                "it's in our cache.")
            else:
                raise Exception("Post #" + str(id_) + " exists even though "
                                "we have no record of it in the cache.")

        if print_progress:
            print("done.")

