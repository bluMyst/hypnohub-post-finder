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
            'tags': 'tag_1 tag_2 tag_3',
            'score': "1337",
            'rating': "s",
            'preview_url': "//foo/foo.png",

            # These two are optional, but a post without them will be assumed
            # to be deleted.
            'author': "foo",
            'file_url': "//foo/foo.png",
        }

        Or it can be an object with those as attributes.

        It's also okay, if the post is deleted, to not include 'author' or
        'file_url'.
        """
        self._data = dict()

        if hasattr(data, 'tags') and isinstance(data.tags, str):
            get_data = lambda k: getattr(data, k)
        else:
            get_data = lambda k: data[k]

        self.id          = int(get_data(data, 'id'))
        self.tags        = get_data('tags').split(' ')
        self.score       = int(get_data('score'))
        self.rating      = get_data('rating')
        self.preview_url = 'http:' + get_data('preview_url')
        self.page_url    = 'http://hypnohub.net/post/show/' + str(self.id) + '/'

        try:
            self.file_url = 'http:' + get_data('file_url')
            self.author   = get_data('author')
        except AttributeError, KeyError:
            self.file_url, self.author = None, None

        assert self.rating in 'sqe'

    def __repr__(self):
        return ("<SimplePost #{self.id}>").format(**locals())

    def __str__(self):
        return ("#{self.id} +{self.score} by {self.author}").format(
            **locals())

    def deleted(self):
        return self.file_url is None or self.author is None

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
    FILENAME = "dataset.pickle"

    def __init__(self):
        if os.path.isfile(self.FILENAME):
            with open(self.FILENAME, 'rb') as data_file:
                raw_dataset = pickle.load(data_file)

            self.good = raw_dataset['good']
            self.bad = raw_dataset['bad']

            # cache = {
            self.cache = raw_datset['cache']
        else:
            self.good = set()
            self.bad = set()
            self.cache = {}

    def save(self):
        """ Save dataset back to pickle file. """
        raw_dataset = {
            'good': self.good,
            'bad': self.bad,
            'cache': self.cache}

        with open(self.FILENAME, 'wb') as data_file:
            pickle.dump(raw_dataset, data_file)

    def get_highest_post(self):
        if len(self.all_posts) == 0:
            self.highest_post = 0
        else:
            self.highest_post = max(self.all_posts.keys())

    def get_id(self, id_):
        """ Get a post from the cache by post id.

            Returns None if the post doesn't exist.
        """
        try:
            return self.all_posts[id_]
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
        new_posts = hhcom.get_simple_posts(
            tags="order:id id:>" + str(self.get_highest_post()),
            limit=100)

        if len(new_posts) == 0:
            return

        if print_progress:
            print("ID#", new_posts[-1].id, end=' ')
            print('-', len(new_posts), "posts", end=' ')
            sys.stdout.flush()

        for post in new_posts:
            if post['status'] != 'deleted':
                self.cache[post.id] = SimplePost(post)

        if print_progress:
            print('-', len(self.all_posts), 'stored')

        self.update_cache(print_progress)

# There should only ever be one of these, since the data is pickled.
dataset = Dataset()

def validate_cache(self, sample_size=300, print_progress=True):
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
        (i, (i in dataset.all_posts)) for i in range(1, highest_post+1)]

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

        if len(hhcom.get_posts("id:" + str(id_))) != int(exists):
            if exists:
                raise Exception("Post #" + str(id_) + " doesn't exist but "
                                "it's in our cache.")
            else:
                raise Exception("Post #" + str(id_) + " exists even though "
                                "we have no record of it in the cache.")

        if print_progress:
            print("done.")

