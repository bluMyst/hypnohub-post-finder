import random
from typing import *

import post_data
import naive_bayes

"""
Uses an NBC and a dataset to retrieve posts from various sort methods, like
"best", "random", etc.
"""

def get_random_uncategorized_post(dataset):
    """ Get a random post from the cache that has yet to be categorized into
    either 'good' or 'bad'.

    Raises an IndexError if the post cache is empty.
    """
    randomly_sorted_posts = [
        i for i in dataset.get_all()
        if i.id not in dataset.good
        and i.id not in dataset.bad]

    return random.choice(randomly_sorted_posts)

class PostGetter(object):
    def __init__(self, dataset):
        self.dataset = dataset
        self.nbc = naive_bayes.NaiveBayesClassifier.from_dataset(self.dataset)

        if len(self.dataset.cache) <= 0:
            raise ValueError("dataset has empty cache")

        # self._best_posts :: List[ Tuple[int, post_data.SimplePost] ]
        self._best_posts = []
        self.seen = set()

    def _get_best_posts(self):
        if len(self._best_posts) >= 1:
            return self._best_posts

        seen = self.dataset.good | self.dataset.bad | self.seen
        self._best_posts = [(self.nbc.predict(i.tags), i)
                           for i in self.dataset.get_all()
                           if i.id not in seen]

        self._best_posts = sorted(self._best_posts, key=lambda x: x[0])

        assert len(self._best_posts) >= 1
        return self._best_posts

    def get_best(self) -> Tuple[int, post_data.SimplePost]:
        best_posts = self._get_best_posts()
        prediction, post = best_posts.pop()
        self.seen.add(post.id)
        return (prediction, post)

    def get_random(self) -> Tuple[int, post_data.SimplePost]:
        id_ = random.choice(list(self.dataset.cache.keys()))
        self.seen.add(id_)
        post = self.dataset.get_id(id_)
        prediction = self.nbc.predict(post.tags)
        return (prediction, post)

    def get_hot(self) -> Tuple[int, post_data.SimplePost]:
        """
        Posts that have a chance of being good and a chance of being totally
        random.
        """
        # Chance of being totally random.
        RANDOM_CHANCE = 0.25

        if random.random() <= RANDOM_CHANCE:
            return self.get_random()
        else:
            return self.get_best()
