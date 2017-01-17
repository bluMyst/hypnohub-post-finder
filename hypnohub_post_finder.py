import requests
import time
import webbrowser
import os
import sys
from pprint import pprint
import bs4
import itertools
import configparser
import textwrap

import ahto_lib
import post_rater

cfg = configparser.ConfigParser()
cfg.read('config.cfg')

def usage():
    print("Usage: {sys.argv[0]} <posts to get>".format(**locals()))

# response XML looks like this:
# <posts count="1337" offset="# posts skipped by page">
#   <post
#     id="1337"
#     tags="foo bar_(asdf) baz"
#     score="0"
#     rating="s"
#     author="foo"
#
#     change="0" source="url" created_at="1465946415" creator_id="1337"
#     md5 file_size="775434" file_url="hypnohub image url"
#     is_shown_in_index="1" preview_url preview_width preview height
#     actual_preview_width actual_preview_height sample_url sample_width
#     sample_height sample_file_size="0" jpeg_url jpeg_width jpeg_height
#     jpeg_file_size="0" status="active" width height
#   />
#
#   <post foo bar>
#
#   <post baz qux>
# </posts>

class Post(object):
    """ Takes a BeautifulSoup of a Hypnohub post's XML data and gives you some
    convenient methods and properties for getting its info.
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
        return ("<Post #{self.id}>").format(**locals())

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

        xml = requests.get("http://hypnohub.net/post/index.xml", params=params)

        # lxml won't install on my system so I have to use an html parser on
        # xml. Trust me: it's better than the hack I was using before.
        #soup = bs4.BeautifulSoup(xml, 'html.parser')
        soup = bs4.BeautifulSoup(xml.text, 'html.parser')

        for post in soup.find_all('post'):
            post = Post(post)

            if not post.deleted:
                self.posts.append(post)

        self._current_page += 1

        time.sleep(cfg['HTTP Requests'].getfloat('Delay Between Requests'))

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

def get_n_good_posts(n, post_iterator, rater=post_rater.rate_post, sort=True):
    """ Returns tuple: ([good posts], number of bad posts filtered, number of
    good posts)

    post_iterator should be a PostGetter or any other iterable of
    Post's. Also: if you're feeling lazy, you can give it a post index
    to start at and it'll make its own PostGetter for you.

    rater should be a number-returning function. Any post where
    rater(post) <= 0 will be filtered out. If sort == True, [good posts] will
    be sorted by rater(post)'s value, desc.
    """

    if not hasattr(post_iterator, '__iter__'):
        post_iterator = PostGetter(int(post_iterator))

    post_filter = lambda post: rater(post) > 0

    good_posts = []
    bad_posts_seen = 0

    for post in post_iterator:
        if post_filter(post):
            good_posts.append(post)

            if len(good_posts) >= n:
                break
        else:
            bad_posts_seen += 1

    if sort:
        good_posts.sort(key=rater, reverse=True)

    good_posts_seen = len(good_posts)

    return good_posts, bad_posts_seen, good_posts_seen

def posts_to_html_file(filename, posts):
    """ Gets an iterable of posts and turns them into an HTML file to display
    them to the user, complete with preview images.

    Includes a bunch of helpful info like a tag-by-tag breakdown of why each
    post got the rating it did.
    """
    with open(filename, 'w') as file_:
        file_.write(textwrap.dedent("""
            <html>
                <head>
                    <style>
                        .entry {
                            margin: 10px;
                            display: inline-table;
                        }

                        .explanation {
                            font-family: "Lucida Console", Monaco, monospace;
                        }

                        .title {
                            font-family: Arial, Helvetica, sans-serif;
                            font-size: 125%;
                            margin: 5px;
                        }

                        .preview {
                            width: 100%;
                        }
                    </style>
                </head><body>
        """))

        for post in posts:
            post_string = str(post).replace('<', '&lt;').replace('>', '&gt;')
            rating, explanation = post_rater.rate_post(post, explain=True)

            file_.write(textwrap.dedent("""
                <div class='entry'>
                    <a href='{post.url}'>
                        <h1 class='title'>
                            {rating:.0f}: {post_string}<br/>
                        </h1>
                        <img class='preview' src='{post.preview_url}'/><br/>
                    </a>
            """).format(**locals()))

            explanation = (
                "<div class='explanation'>"
                + explanation.replace('\n', '<br/>\n')
                + "</div>"
            )

            file_.write(explanation)
            file_.write('</div>')

        file_.write("</body></html>\n")

def posts_to_browser(filename, posts):
    posts_to_html_file(filename, posts)
    webbrowser.open('file://{cwd}/{filename}'.format(
        cwd=os.getcwd(), filename=filename))

if __name__ == '__main__':
    try:
        with open('start_id.txt', 'r') as f:
            start_id = int(f.read())

        print("start_id.txt ->", start_id)
    except IOError:
        start_id = 0

        with open('start_id.txt', 'w') as f:
            f.write(str(start_id))

        print("No start_id.txt. Created as " + str(start_id) + ".")

    try:
        posts_to_get = int(sys.argv[1])
    except IndexError:
        posts_to_get = cfg['General'].getint('Default Posts to Get')
    except ValueError:
        usage()
        exit(1)

    post_getter = PostGetter(start_id)
    good_posts, n_bad, n_good = get_n_good_posts(posts_to_get, post_getter)
    total = n_bad + n_good
    print("Showing {n_good}/{total}, filtered {n_bad}.".format(**locals()))
    posts_to_browser('good_posts.html', good_posts)

    next_post_id = str(post_getter.highest_id + 1)

    response = ahto_lib.yes_no(True, "Next unseen post is {next_post_id}. Save"
        " your progress?".format(**locals()))

    if response:
        with open('start_id.txt', 'w') as f:
            f.write(next_post_id)

        print('Written.')
    else:
        print('Not written.')
