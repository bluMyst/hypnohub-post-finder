import os
import http.server
import urllib.parse
import math

import post_data
import naive_bayes
import post_getters
import http_server.html_generator as html_generator

"""
This file is for interacting with the user's web browser in various ways.
"""

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
