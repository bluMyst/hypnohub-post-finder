import os
import http.server
import urllib.parse
import math
import queue
import threading
import time
import random

import post_data
import naive_bayes
import post_getters
import http_server.html_generator as html_generator

"""
This file is for interacting with the user's web browser in various ways.
"""


class StatefulRequestHandler(object):
    """
    This is a hack to get HTTPRequestHandler's to save state information
    between requests. You have to use it like this:

    request_handler = StatefulRequestHandler(('127.0.0.1',8000))
    request_handler.server.serve_forever()

    The way this works is that on __init__, a StatefulRequestHandler object
    defines a class such that the class has the StatefulRequestHandler in its
    closure. The class is basically a dummy HTTPRequestHandler, that really
    just forwards any interesting calls to our StatefulRequestHandler object. I
    call it a dummy handler.

    If you can't understand what that means, I don't blame you. Just look at
    the code for __init__ and figure it out for yourself. It's actually not
    that difficult of a concept; it's just hard to put into words.

    It's the only way I could think of to preserve any kind of state without
    dumping variables galore into the global namespace of this file.

    'dh' is short for DummyHandler, and 'srh' is short for
    StatefulRequestHandler. The variable names are so terse because they're
    used a lot. They're basically just two namespaces of 'self', like this
    class has a split personality.

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
        """ Will not send 404 if it can't find the file. Just returns False.
        """
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
        elif dh.path.endswith('ico'):
            content_type = 'image/x-icon'
        else:
            # https://stackoverflow.com/questions/1176022/unknown-file-type-mime
            content_type = 'application/octet-stream'

        dh.log_message(f"Serving file at: {dh.path}")

        dh.send_response(200)
        dh.send_header('Content-type', content_type)
        dh.end_headers()

        with open(path, 'r') as f:
            dh.wfile.write(bytes(f.read(), 'utf8'))

        return True


def requires_cache(f):
    """ Blocks the user from loading certain pages unless the Hypnohub cache
    has entries in it.

    Basically, this is a decorator to give a user-friendly error screen instead
    of crashing.
    """
    # TODO: You should be able to update the cache from the web interface, and
    # this decorator should give you the option to do so.
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

        # TODO: API url's should start with /api/
        # Can our url-parser handle multiple levels of directory like that?

        self.PATHS = {
            '/':            [['GET'], self.root],
            '/hot':         [['GET'], self.hot],
            '/best':        [['GET'], self.best],
            '/random':      [['GET'], self.random],
            '/stats':       [['GET'], self.stats],

            '/vote':        [['GET'], self.vote],
            '/save':        [['GET'], self.save],
            '/readConsole': [['GET'], self.readConsole],
            '/console':     [['GET'], self.console],
            '/testConsole': [['GET'], self.testConsole],
        }

        # These are for showing the user a list of all paths with descriptions
        # right next to them. Paths without descriptions won't be shown at all.
        self.PATH_DESCRIPTIONS = {
            '/':            'An index of all URLs on the server.',
            '/hot':         'A random selection of good images.',
            '/save':        'Save your votes so far.',
            '/best':        'The absolute best images we can find for you.',
            '/random':      'Totally random images.',
            '/stats':       'Statistics on... everything!',
            '/testConsole': 'Test the console. (debugging feature)',
        }

        # Used by /readConsole and /console
        self.console_queues = dict()

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
        # TODO: Send code 422 on error. Also check other functions for sending
        #       200 incorrectly.
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
        # Returns 'true' on success. On failure, just crashes :/
        self.dataset.save()
        dh.log_message("Saved self.dataset with good:"
                       + str(len(self.dataset.good))
                       + " and bad:"
                       + str(len(self.dataset.bad)))

        dh.send_response(200)
        dh.send_header('Content-type', 'application/json')
        dh.end_headers()

        dh.wfile.write(bytes("true", 'utf8'))

    def testConsole(self, dh):
        """ Test the console system.
        """
        def test():
            print("Creating console_queue: test")
            console_queue = self.console_queues['test'] = queue.Queue()
            console_queue.put("test line 0")

            for i in range(1, 20):
                time.sleep(random.uniform(0.2, 3))
                console_queue.put(f"test line {i}")

            console_queue.put(None)

        threading.Thread(target=test).start()

        # redirect to /console
        dh.send_response(302)
        dh.send_header('Location', '/console?id=test')
        dh.end_headers()

    def console(self, dh):
        """ Essentially, it's like a browser-based console output that updates
        in real time.

        See docstring for RecommendationRequestHandler.readConsole
        """
        try:
            id_ = dh.query_string['id'][0]
        except KeyError:
            dh.send_response(422)
            return

        self.send_html(dh,
            html_generator.console(id_))

        # at this point there should already be a thread updating
        # self.console_queues[id_], so this method doesn't even need to worry
        # about that.

    def readConsole(self, dh):
        """ An API call used by anything that wants to have scrolling text that
        updates in real time.

        Essentially, it's like a browser-based console output.

        When the client requests to do something that requires a console
        output, they're redirected to "/console?id=foo". (actual URL may have
        been changed) From there, Javascript sends periodic requests for
        "/readConsole?id=foo". Every time it requests this URL, it gets one of
        three JSON responses:

        Empty string (""): No new text to append to the console.
        Non-empty string:  Append this text to the console.
        null:              End of output. Stop requesting /readConsole because
                           there's nothing left to get.
        """
        if 'id' in dh.query_string:
            dh.send_response(200)
            id_ = dh.query_string['id'][0]
        else:
            #TODO: There are a bunch of debug print statements scattered
            # around. Clean them up before commiting.
            print("ERROR INVALID ID BLAH BLAH DEBUG MESSAGE)")
            dh.send_response(422)
            # The 422 (Unprocessable Entity) status code means the server
            # understands the content type of the request entity, and the
            # syntax of the request entity is correct, but was unable to
            # process the contained instructions.
            # https://www.bennadel.com/blog/2434-http-status-codes-for-invalid-data-400-vs-422.htm

            dh.send_header('Content-type', 'application/json')
            dh.end_headers()
            dh.wfile.write(
                bytes('"Error: No \'id\' present in request."', 'utf8'))
            return

        dh.send_header('Content-type', 'application/json')
        dh.end_headers()

        # TODO: Have an error on invalid ID.
        print("Reading from console_queue:", id_)
        queue = self.console_queues[id_]
        lines = []
        dh.wfile.write(bytes("[", 'utf8'))

        first_entry = True

        # TODO: Just use a library to make the JSON.
        while not queue.empty():
            line = queue.get()

            if line is None:
                if not queue.empty():
                    raise Exception(
                        "A console_queue contains None but doesn't end there.")

                line = "null"
                print("Deleting console_queue:", id_)
                del self.console_queues[id_]
            else:
                line = '"' + line + '"'

            if first_entry:
                first_entry = False
            else:
                line = ', ' + line


            dh.wfile.write(bytes(line, 'utf8'))

        # Overwrite final ',' with ']'. JSON doesn't allow trailing commas.
        dh.wfile.write(bytes(']', 'utf8'))

    @requires_cache
    def hot(self, dh):
        score, post = self.post_getter.get_hot()
        self.send_html(
            dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def best(self, dh):
        score, post = self.post_getter.get_best()
        self.send_html(
            dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def random(self, dh):
        score, post = self.post_getter.get_random()
        self.send_html(
            dh,
            html_generator.rating_page_for_post(post, f"score: {score:.2%}"))

    @requires_cache
    def stats(self, dh):
        def header(s):
            spacer_length = (79 - len(s) - 2) / 2
            left = '-' * math.ceil(spacer_length)
            right = '-' * math.floor(spacer_length)
            return left + ' ' + s + ' ' + right

        # This is ugly code but I can't think of a better way to do it.
        s = '\n'.join([
            f"Total good: {len(self.dataset.good)}",
            f"Total bad:  {len(self.dataset.bad)}",
            '',
            f"NBC P(G): {self.nbc.p_g:.2%}",
            '',
            header("GOOD"),
            f"{self.dataset.good}",
            '',
            header("BAD"),
            f"{self.dataset.bad}"
        ])

        s += '\n'
        s += header("100 most common NBC tags") + "\n"
        tag_history = list(self.nbc.tag_history.items())
        tag_history.sort(reverse=True, key=lambda i: i[1][1])
        for tag, (good, total) in tag_history[:100]:
            s += f"{good}/{total}: {tag}\n"

        self.send_html(dh, html_generator.pre_message(s))
