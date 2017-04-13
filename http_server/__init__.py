import yattag
import textwrap
import os
import webbrowser
import http.server
import random
import urllib.parse
import functools

import post_data

"""
This file is for interacting with the user's web browser in various ways.
"""

with open('http_server/main.css', 'r') as css_file:
    CSS = css_file.read()

with open('http_server/vote.js', 'r') as vote_js_file:
    VOTE_JS = vote_js_file.read()

def get_random_uncategorized_post():
    """ Get a random post from the cache that has yet to be categorized
        into either 'good' or 'bad'.

        Raises an IndexError if the post cache is empty.
    """
    randomly_sorted_posts = [
        i for i in post_data.dataset.cache.values()
        if i.id not in post_data.dataset.good
        and i.id not in post_data.dataset.bad]

    return random.choice(randomly_sorted_posts)

class StatefulRequestHandler(object):
    """
    This is a hack to get HTTPRequestHandler's to save state information between
    requests. You have to use it like this:

    request_handler = StatefulRequestHandler(('127.0.0.1',8000))
    request_handler.server.serve_forever()

    The way this works is that on __init__, a StatefulRequestHandler object
    defines a class such that the class has the StatefulRequestHandler in its
    closure. The class is basically a dummy HTTPRequestHandler, that really just
    forwards any interesting calls to our StatefulRequestHandler object. I call
    it a dummy handler.

    If you can't understand what that means, I don't blame you. Just look at
    the code for __init__ and figure it out for yourself. It's actually not
    that difficult of a concept; it's just hard to put into words.

    It's the only way I could think of to preserve any kind of state without
    dumping variables galore into the global namespace of this file.

    'dh' is short for DummyHandler, and 'srh' is short for
    StatefulRequestHandler. The variable names are so terse because they're used
    a lot. They're basically just two namespaces of 'self', like this class has
    a split personality.

    Also the server is built into this class because why not.
    """
    def __init__(self, server_address=('127.0.0.1', 8000)):
        srh = self

        class DummyHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                srh.do_GET(self)

            def do_POST(self):
                srh.do_POST(self)

        # It's a syntax error to try:
        # class self.DummyHandler(...):
        self.DummyHandler = DummyHandler

        self.server = http.server.HTTPServer(server_address, self.DummyHandler)

    def do_GET(self, dh):
        raise NotImplementedError

    def do_POST(self, dh):
        raise NotImplementedError

class AhtoRequestHandler(StatefulRequestHandler):
    """
    Adds a few extra features to StatefulRequestHandler. Read the docstring for
    that one first.

    Example self.PATHS: {
        '/':         [['GET', 'POST'], handler1],
        '/vote':     [['POST'], handler2],
        '/ratings':  [['GET'], handler3],
    }

    Those handlers on the right are called like: handler(self, dh). But the
    'self' is implicite, of course, so if you wanted to manually call a handler
    you'd call it as handler(dh).
    """
    PATH = {}

    def __init__(self, *args, **kwargs):
        # Give all of the handlers a sense of self, as if they were called as
        # normal methods.
        for key, (_, handler) in self.PATH.items():
            self.PATH[key][1] = functools.partial(handler, self)

        super(AhtoRequestHandler, self).__init__(*args, **kwargs)

    def do_POST_and_GET(self, dh):
        dh.path_parsed = urllib.parse.urlparse(dh.path)
        dh.query_string = urllib.parse.parse_qs(dh.path_parsed.query)

        if dh.path_parsed.path not in self.PATHS:
            dh.send_error(404)
            return

        supported_protocols, handler = self.PATHS[dh.path_parsed.path]

        if dh.command not in supported_protocols:
            dh.send_error(501)
            return

        handler(dh)

    do_POST = do_GET = do_POST_and_GET

class RecommendationRequestHandler(AhtoRequestHandler):
    # TODO: Parse URL's properly! dh.path includes all the ?foo=bar&bar=baz
    #       urllib.parse
    def __init__(self, *args, **kwargs):
        self.PATHS = {
            '/':         [['GET'], self.root],
            '/vote':     [['GET'], self.vote],
            '/ratings':  [['GET'], self.ratings],
            '/save':     [['GET'], self.save],
        }
        super(RecommendationRequestHandler, self).__init__(*args, **kwargs)

    def vote(self, dh):
        """ Sends the client 'true' in json for valid arguments and 'false' for
            invalid ones.
        """
        def error():
            dh.wfile.write(bytes("false", 'utf8'))
            print("--------- vote error", dh.query_string, "---------")
            return

        dh.send_response(200)
        dh.send_header('Content-type', 'application/json')
        dh.end_headers()

        if 'direction' not in dh.query_string: error()
        if 'id' not in dh.query_string: error()
        if len(dh.query_string['direction']) != 1: error()
        if len(dh.query_string['id']) != 1: error()

        try:
            direction = dh.query_string['direction'][0].lower()
        except AttributeError:
            error()

        if direction == 'true':
            direction = True
        elif direction == 'false':
            direction = False
        else:
            error()

        try:
            id_ = int(dh.query_string['id'][0])
        except ValueError:
            error()

        print("-"*80)
        print("Adding ID:", id_, "to dataset:", 'good' if direction else 'bad')

        if direction:
            post_data.dataset.good.add(id_)
        else:
            post_data.dataset.bad.add(id_)

        print("Good:", post_data.dataset.good)
        print("Bad:", post_data.dataset.bad)
        print("-"*80)

        dh.wfile.write(bytes("true", 'utf8'))

    def save(self, dh):
        """ Save the dataset to a file. """
        post_data.dataset.save()

        dh.send_response(200)
        dh.send_header('Content-type', 'text')
        dh.end_headers()
        dh.wfile.write(bytes("Saved!", 'utf8'))

    def root(self, dh):
        doc, tag, text = yattag.Doc().tagtext()

        with tag('html'):
            with tag('head'):
                with tag('style'):
                    text(CSS)

            with tag('body'):
                with tag('p'):
                    text("You probably want to go to the ")

                    with tag('a', href='ratings'):
                        text('ratings page')

                    text(".")

        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(doc.getvalue(), 'utf8'))

    def ratings(self, dh):
        doc, tag, text = yattag.Doc().tagtext()
        random_post = get_random_uncategorized_post()

        with tag('html'):
            with tag('head'):
                with tag('style'):
                    text(CSS)

                with tag('script', type='text/javascript'):
                    doc.asis("var post_id = " + str(random_post.id))
                    doc.asis(VOTE_JS)

            with tag('body'):
                with tag('h1'):
                    text('ID#: ' + str(random_post.id))

                with tag('p'):
                    text('A (up) and Z (down) to vote. ')

                    with tag('a', href='/save'):
                        text("Click here to save your votes.")

                with tag('h1'):
                    with tag('div', klass='vote_controls'):
                        with tag('a', href='#', klass='upvote',
                                onclick='upvote()'):
                            text('/\\')

                        doc.stag('br')
                        doc.stag('br')

                        with tag('a', href='#', klass='downvote',
                                onclick='downvote()'):
                            text('\\/')

                with tag('a', href=random_post.page_url):
                    doc.stag('img', src=random_post.file_url,
                            klass="rating_image")

        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(doc.getvalue(), 'utf8'))
