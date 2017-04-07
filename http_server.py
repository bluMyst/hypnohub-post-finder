import yattag
import textwrap
import os
import webbrowser
import http.server

import post_rater

"""
This file is for interacting with the user's web browser in various ways.
"""

FILENAME = 'good_posts.html'

CSS = textwrap.dedent("""
    body {
        font-family: Arial, Helvetica, sans-serif;
        background: #000;
        color: #00e0e0;
    }

    a {
        color: #00e0e0;
    }

    .post {
        margin: 10px;
        display: inline-table;
        width: 30%;
        background: #111;
    }

    .explanation {
        font-family: "Lucida Console", Monaco, monospace;
        padding: 0 10%;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .title {
        font-size: 125%;
        margin: 5px;
        text-align: center;
    }

    .preview {
        max-width: 100%;
        margin: auto;
        display: block;
        height: 300px;
    }
""")

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
    def __init__(self, *args, **kwargs):
        super(RecommendationRequestHandler, self).__init__(*args, **kwargs)

    def do_GET(self, dh):
        if dh.client_address[0] != '127.0.0.1':
            dh.send_error(403, explain="Only serving 127.0.0.1, not "
                          + dh.client_address[0])
            return

        if dh.path == '/':
            self.make_root_page(dh)
        elif dh.path == '/ratings':
            self.make_rating_page(dh)
        else:
            dh.send_error(404)
            return

    def make_root_page(self, dh):
        doc, tag, text = yattag.Doc().tagtext()

        with tag('html'):
            with tag('head'):
                with tag('style'):
                    text(CSS)

            with tag('body'):
                with tag('p'):
                    text("Loading... (not really)")
                    text(str(self.test_counter))
                    self.test_counter += 1

        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(doc.getvalue(), 'utf8'))

    def make_rating_page(self, dh):
        doc, tag, text = yattag.Doc().tagtext()

        with tag('html'):
            with tag('head'):
                with tag('style'):
                    text(CSS)

            with tag('body'):
                with tag('p'):
                    text("This will be the rating page once I get stuff "
                         "working.")

        dh.send_response(200)
        dh.send_header('Content-type', 'text/html')
        dh.end_headers()
        dh.wfile.write(bytes(doc.getvalue(), 'utf8'))

def posts_to_html(posts):
    """ Gets an iterable of posts and turns them into HTML to display them to
    the user, complete with preview images.

    Includes a bunch of helpful info like a tag-by-tag breakdown of why each
    post got the rating it did.
    """
    doc, tag, text = yattag.Doc().tagtext()

    #with open(filename, 'w') as file_:
    with tag('html'):
        with tag('head'):
            with tag('style'):
                text(CSS)

        with tag('body'):
            for post in posts:
                rating, explanation = post_rater.rate_post(post, explain=True)

                with tag('div', klass='post'):
                    with tag('a', href=post.url):
                        with tag('h1', klass='title'):
                            text('{rating:.0f}: {post_string}'.format(
                                rating=rating, post_string=str(post)))
                            doc.stag('br')

                        doc.stag('img', klass='preview', src=post.preview_url)
                        doc.stag('br')

                    with tag('div', klass='explanation'):
                        for line in explanation.split('\n'):
                            text(line)
                            doc.stag('br')

    return doc.getvalue()

def posts_to_browser(posts):
    html = posts_to_html(posts)

    with open(FILENAME, 'w') as file_:
        file_.write(html)

    webbrowser.open('file://' + os.getcwd() + os.sep + FILENAME)
