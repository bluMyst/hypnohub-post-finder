from typing import *
import sys
import math

if __name__ == '__main__':
    print("Loading cache...", end=' ')
    sys.stdout.flush()

import naive_bayes
import post_data

# TODO: py.test in this file

if __name__ == '__main__':
    print("done.")
    nbc = naive_bayes.naive_bayes_classifier
    dataset = post_data.dataset
    predictions_and_posts = [(nbc.predict(i.tags), i) for i in dataset.get_all()]

    predictions_and_posts = sorted(predictions_and_posts, key=lambda x: x[0])

    if __debug__:
        for i, post in predictions_and_posts:
            if i < 0 or i > 1.6:
                nbc.predict(post.tags, debug=True)
                print(i, post)
                exit(1)

    for prediction, post in predictions_and_posts:
        if post.id not in dataset.good:
            print(prediction, post, post.page_url)
