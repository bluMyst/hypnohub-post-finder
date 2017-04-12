import yattag
import textwrap
import os
import webbrowser
import http.server
import random

import post_rater
import post_data

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

            with tag('body'):
                with tag('h1'):
                    text('ID#: ' + str(random_post.id))

                with tag('p'):
                    text('A (up) and Z (down) to vote.')

                with tag('h1'):
                    with tag('a', href='#', id='upvote'):
                        text('/\\')

                    doc.stag('br')
                    doc.stag('br')

                    with tag('a', href='#', id='downvote'):
                        text('\\/')

                with tag('a', href=random_post.page_url):
                    doc.stag('img', src=random_post.file_url,
                             style="display: block;")

                with tag('script', type='text/javascript'):
                    doc.asis("var post_id = " + str(random_post.id))
                    doc.asis("""
                        var has_voted = false

                        function vote(direction) {
                            // direction == true: upvote
                            // direction == false: downvote
                            if (!has_voted) {
                                var confirmation = confirm(
                                    "Want to "
                                    + (direction ? 'upvote' : 'downvote')
                                    + " the current image?"
                                )

                                if (!confirmation) { return }

                                has_voted = true

                                var oReq = new XMLHttpRequest()
                                oReq.addEventListener("load",
                                    function(){
                                        alert('Voted: ' + direction.toString())
                                        location.reload()
                                    }
                                )

                                oReq.open(
                                    "POST",
                                    "/vote?direction=" + direction.toString()
                                    + "&id=" + post_id.toString()
                                )

                                oReq.send()
                            }
                        }

                        function upvote()   {vote(true)}
                        function downvote() {vote(false)}

                        document.getElementById('upvote').addEventListener(
                            "click", upvote)

                        document.getElementById('downvote').addEventListener(
                            "click", downvote)

                        document.addEventListener('keyup', function(event){
                            if (event.key === 'a') {
                                upvote()
                            } else if (event.key === 'z') {
                                downvote()
                            }
                        })
                    """)

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
