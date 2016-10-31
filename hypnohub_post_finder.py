import requests
import time
import webbrowser
import os
import sys
from pprint import pprint
import xml.etree.ElementTree as ElementTree
import itertools

import ahto_lib
import post_rater

DELAY_BETWEEN_REQUESTS = 1 # seconds
DEFAULT_POSTS_TO_GET = 50

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

        try:
            et = ElementTree.fromstring(xml.content)
        except ElementTree.ParseError:
            # This probably means there's an invalid entity, like &euro;, that
            # isn't handled by the default parser.
            #
            # By default, the parser knows about &lt;, &gt;, etc. But we need
            # tell it how to handle more exotic stuff like &atilde; or &fnof;.
            # This is normally done in a DTD, but I can't figure out if
            # HypnoHub has an external DTD, and there isn't any DTD information
            # in the XML that it sends.
            #
            # It looks like you can replace entities with entire strings, not
            # just single characters. So that's pretty cool.

            # TODO: Create a class that can take any arbitrary entity.
            entity_replacements = {
                # Standard entities, just in case we need them.
                'gt':    '>',
                'lt':    '<',
                'nbsp':  ' ',
                'amp':   '&',

                # A few of the weird entities that aren't normally supported.
                'atilde':  '[atilde]',
                'bull':    '[bull]',
                'euro':    '[euro]',
                'fnof':    '[fnof]',
                'sbquo':   '[sbquo]',
                'sect':    '[sect]',
                'sup1':    '[sup1]',
                'sup3':    '[sup3]',
                'yen':     '[yen]'
            }

            parser = ElementTree.XMLParser()
            parser._parser.UseForeignDTD(True)
            parser.entity.update(entity_replacements)

            et = ElementTree.fromstring(xml.content, parser=parser)

        self.posts += [HypnohubPost(post) for post in et.iter('post')]
        self.posts =  [i for i in self.posts if not i.deleted]
        self.current_page += 1

        for i in self.posts:
            if int(i.id) > self.highest_id:
                self.highest_id = int(i.id)

        time.sleep(DELAY_BETWEEN_REQUESTS)

    def __next__(self):
        if len(self.posts) > 0:
            return self.posts.pop()

        self.get_next_batch()

        if len(self.posts) > 0:
            return self.__next__()
        else:
            raise StopIteration

    def get_n_good_posts(self, n, criteria_function=post_rater.post_filter):
        """ returns (good_posts, bad_posts) """
        good_posts = []
        bad_posts  = []
        for post in self:
            if criteria_function(post):
                good_posts.append(post)
            else:
                bad_posts.append(post)

            if len(good_posts) >= posts_to_get:
                return good_posts, bad_posts


class HypnohubPost(object):
    # Used by overall_rating
    def __init__(self, element_tree):
        self.element_tree = element_tree

    def __getattr__(self, name):
        # only called for invalid attr
        try:
            return self.element_tree.attrib[name]
        except KeyError:
            raise AttributeError(name)

    def __repr__(self):
        return ("<HypnohubPost #{self.id}>").format(**locals())

    def __str__(self):
        return ("Post#{self.id} rated {self.score} by {self.author}").format(
            **locals())

    __getitem__ = __getattr__

    @ahto_lib.lazy_property
    def tags(self):
        return self.element_tree.attrib['tags'].split(' ')

    @ahto_lib.lazy_property
    def url(self):
        return "http://hypnohub.net/post/show/" + self.id + "/"

    def has_any(self, tags):
        #return any(tag in self.tags for tag in tags)
        for tag in tags:
            if tag in self.tags:
                return True

        return False

    def has_all(self, tags):
        #return all(tag in self.tags for tag in tags)
        for tag in tags:
            if tag not in self.tags:
                return False

        return True

    @ahto_lib.lazy_property
    def deleted(self):
        return 'file_url' not in self.element_tree.attrib

def posts_to_html_file(filename, posts):
    with open(filename, 'w') as file_:
        html_start = "<html><body>\n"
        html_end = "</body></html>\n"

        file_.write(html_start)

        for post in posts:
            post_string = str(post).replace('<', '&lt;').replace('>', '&gt;')
            rating = post_rater.rate_post(post)

            file_.write("<a href='{post.url}'>{rating}:"
                " {post_string}<br/>\n".format(**locals()))

            file_.write("<img src='{post.preview_url}'/>\n".format(**locals()))
            file_.write("</a><br/>\n")

            # Detailed rating info.
            for tag in post.tags:
                if tag in post_rater.TAG_RATINGS:
                    tag_rating = post_rater.TAG_RATINGS[tag]
                    file_.write(str(tag_rating) + ": " + tag + "<br/>\n")

            file_.write(str(post_rater.score_factor(int(post.score)))
                + ' score factor<br/>\n')

            file_.write(str(rating))

            file_.write("<br/><br/>\n")

        file_.write(html_end)

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
