import requests
import time
import webbrowser
import os
import sys
from pprint import pprint
import xml.etree.ElementTree as ElementTree

import post_rater

DELAY_BETWEEN_REQUESTS = 1 # seconds
DEFAULT_POSTS_TO_GET = 50

def usage():
    print("Usage: {sys.argv[0]} <posts to get>".format(**locals()))

def get_post_index(limit, tags=None):
    params = {'tags':tags} if tags else {}

    if limit >= 100:
        limits_per_page = ( [100]*(limit/100) ) # integer division rounds down

        if limit%100: limits_per_page += [limit%100]
    else:
        limits_per_page = [limit]

    print("limit of {limit} -> ".format(**locals()), end=' ')
    pprint(limits_per_page)
    print()

    for page, limit in enumerate(limits_per_page):
        params['page'], params['limit'] = page+1, limit
        r = requests.get("http://hypnohub.net/post/index.xml", params=params)
        yield r
        #print "\rGot post {}/{}".format(page+1, len(limits_per_page)),
        print("Got url: {r.url}".format(**locals()))
        time.sleep(DELAY_BETWEEN_REQUESTS)

# get_post_index response XML looks like this:
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

def get_posts(limit, tags=None):
    posts = []

    for http_response in get_post_index(limit, tags):
        #et = ElementTree.fromstring(http_response.text)
        try:
            et = ElementTree.fromstring(http_response.content)
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
            entity_replacements = [
                # Standard entities, just in case we need them.
                ('gt', '>'),
                ('lt', '<'),
                ('nbsp', ' '), # TODO: not a non-breaking space
                ('amp', '&'),

                # A few of the weird entities that aren't normally supported.
                ('atilde', '[atilde]'),
                ('bull', '[bull]'),
                ('euro', '[euro]'),
                ('fnof', '[fnof]'),
                ('sbquo', '[sbquo]'),
                ('sect', '[sect]'),
                ('sup1', '[sup1]'),
                ('sup3', '[sup3]'),
                ('yen', '[yen]')
            ]

            parser = ElementTree.XMLParser()
            parser._parser.UseForeignDTD(True)

            for k, v in entity_replacements:
                parser.entity[k] = v

            et = ElementTree.fromstring(http_response.content, parser=parser)

        posts += list(map(HypnohubPost, et.iter('post')))

    return posts

def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))

        return getattr(self, attr_name)

    return _lazy_property

class HypnohubPost(object):
    # Used by overall_rating
    def __init__(self, element_tree):
        self.element_tree = element_tree

    def __getattr__(self, name):
        # only called for invalid attr
        return self.element_tree.attrib[name]

    def __repr__(self):
        return ("<HypnohubPost #{self.id}>").format(**locals())

    def __str__(self):
        rating = self.overall_rating()
        return ("Post#{self.id} self-rated {rating} others-rated {self.score}"
            " by {self.author}").format(**locals())

    __getitem__ = __getattr__

    @lazy_property
    def tags(self):
        return self.element_tree.attrib['tags'].split(' ')

    @lazy_property
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

    @lazy_property
    def deleted(self):
        return 'file_url' not in self.element_tree.attrib

#def post_filter(post):
#    blacklist = ['death', 'scat', 'fart', 'animals_only', 'dolores_umbridge',
#        'alvin_and_the_chipmunks', 'vore', 'the_simpsons',
#        'animal_transformation', 'lilo_and_stich', 'kaa', 'jiminy_cricket',
#        'weight_gain', 'huge_nipples', 'huge_lips', 'large_lips',
#        'daria_(series)', 'fat', 'nightmare_fuel', 'vore', 'petrification',
#        'bimbofication', 'breast_expansion', 'fisting', 'pregnant', 'human_pet',
#        'ghost_clown', 'ed_edd_n_eddy', 'robotization', 'chaoscroc']
#
#    return (
#        not post.has_any(blacklist)
#        and post.score >= 20
#        and not post.deleted
#    )

def posts_to_html_file(filename, posts):
    with open(filename, 'w') as file_:
        html_start = "<html><body>\n"
        html_end = "</body></html>\n"

        file_.write(html_start)

        for post in posts:
            post_string = str(post).replace('<', '&lt;').replace('>', '&gt;')
            post_html = "<a href='{post.url}'>{post_string}<br/>"
            post_html += "<img src='{post.preview_url}'/>".format(**locals())
            post_html += "</a><br/><br/>\n"
            post_html = post_html.format(**locals())
            file_.write(post_html)

        file_.write(html_end)

if __name__ == '__main__':
    try:
        start_id = int(open('start_id.txt', 'r').read())
        print("start_id.txt ->", start_id)
    except IOError:
        open('start_id.txt', 'w').write('0')
        start_id = 0
        print("No start_id.txt. Created as 0.")

    tags = "order:id id:>={start_id}".format(**locals())

    try:
        posts = get_posts(int(sys.argv[1]), tags)
    except ValueError:
        usage()
        exit(1)
    except IndexError:
        posts = get_posts(DEFAULT_POSTS_TO_GET, tags)

    print("Posts: " + str(len(posts)), end=' ')
    good_posts = list(filter(post_rater.post_filter, posts))
    print(" reduced to: " + str(len(good_posts)))

    posts_to_html_file('urls.html', good_posts)
    webbrowser.open('file://{cwd}/urls.html'.format(cwd=os.getcwd()))

    # Prettiest code of all time. Beautiful.
    invert_func = lambda func: lambda *args, **kwargs: not func(*args, **kwargs)
    posts_to_html_file('filtered_urls.html', list(filter(invert_func(post_rater.post_filter), posts)))
    webbrowser.open('file://{cwd}/filtered_urls.html'.format(cwd=os.getcwd()))

    next_post_id = str(int(posts[-1].id) + 1)

    response = input(
        ('Highest post id should be {}. '
        'Write that+1 ({}) to start_id.txt? [Yn]').format(
            posts[-1].id, next_post_id)
    )

    if response.lower() != 'n':
        open('start_id.txt', 'w').write(next_post_id)
        print('Written.')
    else:
        print('Not written.')
