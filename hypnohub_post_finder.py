import requests
import time
import webbrowser
import os
import sys
from pprint import pprint
import bs4
import itertools

import ahto_lib
import post_rater

DELAY_BETWEEN_REQUESTS =  1 # seconds
DEFAULT_POSTS_TO_GET   = 50

# I don't remember exactly how this works, but I think hypnohub will only let
# you get so many images per request.
LIMIT_PER_PAGE = 100

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

class HypnohubPostGetter(object):
    """Gets HypnohubPost's. Works like an iterator.

    It'll get them in chunks of limit_per_page at a time.
    """
    def __init__(self, limit_per_page=LIMIT_PER_PAGE, tags="", starting_index=0):
        self.limit_per_page = limit_per_page
        self.tags = tags + " order:id id:>=" + str(starting_index)
        self.starting_index = starting_index

        self.current_page = 1
        self.posts = []
        self.highest_id = -1

    def __iter__(self):
        return self

    def get_next_batch(self):
        params = {
            'page': self.current_page,
            'limit': self.limit_per_page}

        if self.tags:
            params['tags'] = self.tags

        xml = requests.get("http://hypnohub.net/post/index.xml", params=params)
        # lxml won't install on my system so I have to use an html parser on
        # xml. Trust me; it's better than the hack I was using before.
        #soup = bs4.BeautifulSoup(xml, 'html.parser')
        soup = bs4.BeautifulSoup(xml.text, 'html.parser')

        for post in soup.find_all('post'):
            post = HypnohubPost(post)

            if not post.deleted:
                self.posts.append(post)

        self.current_page += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    def __next__(self):
        for _ in range(0, 25):
            if len(self.posts) > 0:
                next_post, self.posts = self.posts[0], self.posts[1:]
                self.highest_id = max(self.highest_id, next_post.id)
                return next_post

            self.get_next_batch()

        raise StopIteration

    def get_n_good_posts(self, n, criteria_function=post_rater.post_filter, sort=True):
        """ returns (good_posts, bad_posts) """
        good_posts = []
        bad_posts  = []
        for post in self:
            if criteria_function(post):
                good_posts.append(post)
            else:
                bad_posts.append(post)

            if len(good_posts) >= n:
                break

        good_posts.sort(key=post_rater.rate_post, reverse=True)
        bad_posts.sort( key=post_rater.rate_post, reverse=True)

        return good_posts, bad_posts

class HypnohubPost(object):
    def __init__(self, post_soup):
        self.post_soup = post_soup

    def __getattr__(self, name):
        # only called for invalid attr
        try:
            return self.post_soup[name]
        except KeyError:
            raise AttributeError(name)

    __getitem__ = __getattr__

    def __repr__(self):
        return ("<HypnohubPost #{self.id}>").format(**locals())

    def __str__(self):
        return ("Post#{self.id} rated {self.score} by {self.author}").format(
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
        return any(tag in self.tags for tag in tags)

    def has_all(self, tags):
        return all(tag in self.tags for tag in tags)

    @ahto_lib.lazy_property
    def deleted(self):
        try:
            self.post_soup['file_url']
        except KeyError:
            return True
        else:
            return False
        #return 'file_url' not in self.post_soup

    @ahto_lib.lazy_property
    def preview_url(self):
        # self.post_soup['preview_url'] example:
        # '//hypnohub.net//data/preview/2eea10e9b65a2de8e84ab88dcfd90575.jpg'
        return 'http:' + self.post_soup['preview_url']

def posts_to_html_file(filename, posts):
    with open(filename, 'w') as file_:
        file_.write("<html><body>\n")

        for post in posts:
            post_string = str(post).replace('<', '&lt;').replace('>', '&gt;')
            rating = post_rater.rate_post(post)
            score_factor = post_rater.score_factor(post.score)

            file_.write((
                "<a href='{post.url}'>\n"
                "    {rating}: {post_string}<br/>\n"
                "    <img src='{post.preview_url}'/><br/>\n"
                "</a>\n"
            ).format(**locals()))

            # Detailed rating info.
            for tag in post.tags:
                if tag in post_rater.TAG_RATINGS:
                    tag_rating = post_rater.TAG_RATINGS[tag]
                    file_.write("{tag_rating}: {tag}<br/>\n".format(**locals()))

            file_.write((
                'score_factor({post.score}) -> {score_factor}<br/>\n'
                '----------------------------<br/>\n'
                '{rating}<br/>\n'
                '<br/>\n'
            ).format(**locals()))

        file_.write("</body></html>\n")

def posts_to_browser(filename, posts):
    posts_to_html_file(filename, posts)
    webbrowser.open('file://{cwd}/{filename}'.format(
        cwd=os.getcwd(), filename=filename))

if __name__ == '__main__':
    try:
        start_id = int(open('start_id.txt', 'r').read())
        print("start_id.txt ->", start_id)
    except IOError:
        open('start_id.txt', 'w').write('0')
        start_id = 0
        print("No start_id.txt. Created as 0.")

    try:
        posts_to_get = int(sys.argv[1])
    except IndexError:
        posts_to_get = DEFAULT_POSTS_TO_GET
    except ValueError:
        usage()
        exit(1)

    post_getter = HypnohubPostGetter(starting_index=start_id)
    good_posts, bad_posts = post_getter.get_n_good_posts(posts_to_get)

    print(len(good_posts) + len(bad_posts), "posts reduced to:", len(good_posts))

    posts_to_browser('good_posts.html', good_posts)
    posts_to_browser('bad_posts.html', bad_posts)

    next_post_id = str(post_getter.highest_id + 1)

    response = ahto_lib.yes_no(True, 'Highest post id should be {}. Write'
        ' that+1 ({}) to start_id.txt?'.format(
            post_getter.highest_id, next_post_id))

    if response:
        open('start_id.txt', 'w').write(next_post_id)
        print('Written.')
    else:
        print('Not written.')
