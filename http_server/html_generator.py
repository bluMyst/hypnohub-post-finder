from typing import *

import yattag

"""
Generates HTML for use by the http server.
"""

def css_link():
    doc = yattag.Doc()
    doc.stag('link', rel='stylesheet', type='text/css', href='/main.css')
    return doc.getvalue()

def rating_page_for_post(post, message=None):
    """
    A page where you can rate a single Hypnohub post.
    """
    doc, tag, text, line = yattag.Doc().ttl()

    with tag('html'):
        with tag('head'):
            doc.asis(css_link())

            with doc.tag('script', type='text/javascript'):
                doc.asis(f"var post_id = {post.id}")

            with doc.tag('script', type='text/javascript', src="/vote.js"):
                pass

        with tag('body'):
            with tag('h1'):
                text(f'ID#: {post.id}')
                if message: text(f' - {message}')

            with tag('p'):
                text('A (up) and Z (down) to vote. ')
                line('a', "Click here to save your votes.", href='/save')

            with tag('div', klass='voting_area'):
                with tag('div', klass='vote_controls'):
                    line('a', '/\\', href='#', klass='vote upvote',
                         onclick='upvote()')

                    line('a', r'\/', href='#', klass='vote downvote',
                         onclick='downvote()')

                with tag('a', href=post.page_url):
                    doc.stag('img', src=post.sample_url, klass="rating_image")

    return doc.getvalue()

def path_index(paths_and_descriptions: List[Tuple[str, str]]):
    doc, tag, text, line = yattag.Doc().ttl()

    with tag('html'):
        with tag('head'):
            doc.asis(css_link())

        with tag('body'):
            line('p', 'List of pages:')

            with tag('table'):
                for path, description in paths_and_descriptions:
                    with tag('tr'):
                        with tag('td'):
                            line('a', path, href=path)

                        line('td', description)

    return doc.getvalue()

def simple_message(paragraphs):
    """
    paragraphs is List[str] or just str
    """
    if type(paragraphs) == str:
        paragraphs = [paragraphs]

    doc, tag, text, line = yattag.Doc().ttl()

    with tag('html'):
        with tag('head'):
            doc.asis(css_link())

        with tag('body'):
            for paragraph in paragraphs:
                line('p', paragraph)

    return doc.getvalue()
