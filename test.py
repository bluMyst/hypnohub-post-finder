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
    dataset = post_data.Dataset()
    nbc = naive_bayes.NaiveBayesClassifier.from_dataset(dataset)
    predictions_and_posts = [(nbc.predict(i.tags), i) for i in dataset.get_all()]

    predictions_and_posts = sorted(predictions_and_posts, key=lambda x: x[0])

    for prediction, post in predictions_and_posts[-100:]:
        if post.id not in dataset.good | dataset.bad:
            print(prediction, post, post.page_url)
