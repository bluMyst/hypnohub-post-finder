import yattag
import textwrap
import os
import webbrowser

import post_rater

"""
This file is for interacting with the user's web browser in various ways.
"""

FILENAME = 'good_posts.html'

CSS = textwrap.dedent("""
    body {
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
        font-family: Arial, Helvetica, sans-serif;
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
