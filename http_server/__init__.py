import yattag
import textwrap
import os
import webbrowser
import http.server
import random
import urllib.parse
import functools
from typing import *

import post_data
import naive_bayes
import ahto_lib
import post_getters
import http_server.html_generator as html_generator

"""
This file is for interacting with the user's web browser in various ways.
"""

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
        '/':         [['GET', 'POST'], self.handler1],
        '/vote':     [['POST'], self.handler2],
        '/ratings':  [['GET'], self.handler3],
    }

    Those handlers on the right are called like: handler(self, dh).

    If there's no handler for a specific file, and the file ends in '.js',
    '.css', '.html', or '.htm', we'll retrieve that file from ./http_server/
    This path is relative to the person who created the handler, and not to the
    handler itself. The content-type will be whatever the extension should
    naturally have. For example, 'foo.html' would be 'text/html'. You can
    disable this feature by setting SERVE_FILES to False.
    """
    PATHS = {}
    SERVE_FILES = True
    FILE_DIR = os.path.abspath("./http_server/")

    def do_POST_and_GET(self, dh):
        dh.path_parsed = urllib.parse.urlparse(dh.path)
        dh.query_string = urllib.parse.parse_qs(dh.path_parsed.query)

        if dh.path_parsed.path not in self.PATHS:
            if not self.SERVE_FILES or not self.serve_from_filesystem(dh):
                dh.send_error(404)

            return

        supported_protocols, handler = self.PATHS[dh.path_parsed.path]

        if dh.command not in supported_protocols:
            dh.send_error(501)
            return

        handler(dh)

    do_POST = do_GET = do_POST_and_GET

    def serve_from_filesystem(self, dh) -> bool:
        """ Will not send 404 if it can't find the file. Just returns False. """
        path = os.path.abspath(self.FILE_DIR + dh.path)

        if os.path.commonprefix([path, self.FILE_DIR]) != self.FILE_DIR:
            dh.log_message(f"Possible directory traversal attack: {dh.path!r}")
            return False

        if not os.path.isfile(path):
            return False

        if dh.path.endswith('.html') or dh.path.endswith('.htm'):
            content_type = 'text/html'
        elif dh.path.endswith('.js'):
            content_type = 'text/javascript'
        elif dh.path.endswith('css'):
            content_type = 'text/css'

        dh.log_message(f"Serving file at {path} (parsed from: {dh.path})")

        dh.send_response(200)
        dh.send_header('Content-type', content_type)
        dh.end_headers()

        with open(path, 'r') as f:
            dh.wfile.write(bytes(f.read(), 'utf8'))

        return True

def requires_cache(f):
    def new_f(self, dh, *args, **kwargs):
        if self.dataset.cache_empty:
            html = html_generator.simple_message(
                "The Hypnohub cache is empty! :(")
            self.send_html(dh, html)
        else:
            return f(self, dh, *args, **kwargs)

    return new_f

class RecommendationRequestHandler(AhtoRequestHandler):
    def __init__(self, *args, **kwargs):
        super(RecommendationRequestHandler, self).__init__(*args, **kwargs)

        self.PATHS = {
            '/':            [['GET'], self.root],
            '/vote':        [['GET'], self.vote],
            '/hot':         [['GET'], self.hot],
            '/save':        [['GET'], self.save],
            '/best':        [['GET'], self.best],
            '/random':      [['GET'], self.random],
            '/stats':       [['GET'], self.stats],
        }

        # These are for showing the user a list of all paths with descriptions
        # right next to them. Paths without descriptions won't be shown at all,
        # because they're usually for behind-the-scenes work.
        self.PATH_DESCRIPTIONS = {
            '/':        'An index of all URLs on the server.',
            '/hot':     'A random selection of good images.',
            '/save':    'Save your votes so far.',
            '/best':    'The absolute best images we can find for you.',
            '/random':  'Totally random images.',
            '/stats':   "Statistics on... everything!",
        }

        self.dataset = post_data.Dataset()
        self.nbc = naive_bayes.NaiveBayesClassifier.from_dataset(self.dataset)
        self.post_getter = post_getters.PostGetter(self.dataset, self.nbc)

    def send_html(self, dh, html_text):
        assert type(html_text) == str
        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(html_text, 'utf8'))

    def root(self, dh):
        paths_and_descriptions = ((path, self.PATH_DESCRIPTIONS[path])
                                  for path in self.PATHS.keys()
                                  if path in self.PATH_DESCRIPTIONS)
        self.send_html(dh, html_generator.path_index(paths_and_descriptions))

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

        if ('direction' not in dh.query_string
                or 'id' not in dh.query_string
                or len(dh.query_string['direction']) != 1
                or len(dh.query_string['id']) != 1):
            error()

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

        dh.log_message(f"Adding ID: {id_} to dataset: "
                       + ('good' if direction else 'bad'))

        if direction:
            self.dataset.good.add(id_)
        else:
            self.dataset.bad.add(id_)

        dh.wfile.write(bytes("true", 'utf8'))

    def save(self, dh):
        """ Save the dataset to a file. """
        self.dataset.save()
        dh.log_message("Saved self.dataset with good:"
                       + str(len(self.dataset.good))
                       + " and bad:"
                       + str(len(self.dataset.bad)))

        self.send_html(dh, html_generator.simple_message(["Saved!"]))

    @requires_cache
    def hot(self, dh):
        score, post = self.post_getter.get_hot()
        self.send_html(dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def best(self, dh):
        score, post = self.post_getter.get_best()
        self.send_html(dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def random(self, dh):
        score, post = self.post_getter.get_random()
        self.send_html(dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def stats(self, dh):
        s = textwrap.dedent(f"""
            Total good: {len(self.dataset.good)}
            Total bad:  {len(self.dataset.bad)}

            NBC P(G): {self.nbc.p_g:.2%}

            ------------------------------ GOOD ------------------------------
            {self.dataset.good}

            ------------------------------ BAD ------------------------------
            {self.dataset.bad}

            ---------------------- 100 most common NBC tags: -------------------
        """)

        tag_history = list(self.nbc.tag_history.items())
        tag_history = sorted(tag_history, reverse=True, key=lambda i: i[1][1])
        tag_history = tag_history[:100]
        for tag, (good, total) in tag_history:
            s += f"{good}/{total}: {tag}\n"

        self.send_html(dh, html_generator.pre_message(s))
