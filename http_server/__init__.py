import yattag
import textwrap
import os
import webbrowser
import http.server
import random

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

    If that doesn't make any sense, I don't blame you. I can barely wrap my own
    head around it and *I* wrote the code! It's just the only way I could think
    of to preserve any kind of state without dumping variables galore into the
    global namespace of this file.

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

class RecommendationRequestHandler(StatefulRequestHandler):
    # TODO: Parse URL's properly! dh.path includes all the ?foo=bar&bar=baz
    #       urllib.parse
    def do_GET(self, dh):
        if dh.client_address[0] != '127.0.0.1':
            dh.send_error(403, explain="Only serving 127.0.0.1, not "
                          + dh.client_address[0])
            return

        if dh.path == '/':
            self.make_root_page(dh)
        elif dh.path == '/ratings':
            self.make_rating_page(dh)
        elif dh.path == '/vote':
            dh.send_error(501)
        else:
            dh.send_error(404)
            return

    def do_POST(self, dh):
        if dh.path.startswith('/vote'):
            self.vote(dh)
        else:
            dh.send_error(501)

    def vote(self, dh):
        print("requestline:", dh.requestline)
        dh.log_message("requestline: " + repr(dh.requestline))

        dh.send_response(200)
        dh.send_header('Content-type', 'text')
        dh.end_headers()

        dh.wfile.write(bytes("Got it! Thanks!\n", 'utf8'))

    def make_root_page(self, dh):
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

    def make_rating_page(self, dh):
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
                    text('A (up) and Z (down) to vote.')

                with tag('h1'):
                    with tag('a', href='#', onclick='upvote()'):
                        text('/\\')

                    doc.stag('br')
                    doc.stag('br')

                    with tag('a', href='#', onclick='downvote()'):
                        text('\\/')

                with tag('a', href=random_post.page_url):
                    doc.stag('img', src=random_post.file_url,
                            style="height: 100%;")

        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(doc.getvalue(), 'utf8'))
