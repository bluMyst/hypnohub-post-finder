import random
from typing import List, Tuple
import itertools

import post_data
import naive_bayes

"""
Uses an NBC and a dataset to retrieve posts from various sort methods, like
"best", "random", etc.
"""


class PostGetter(object):
    def __init__(self, dataset=None, nbc=None):
        if dataset is None:
            dataset = post_data.Dataset()
        self.dataset = dataset

        if nbc is None:
            nbc = naive_bayes.NaiveBayesClassifier.from_dataset(self.dataset)
        self.nbc = nbc

        # self._best_posts :: List[ Tuple[int, post_data.SimplePost] ]
        self._best_posts = []
        self.seen = set()

    def _get_best_posts(self) -> List[Tuple[int, post_data.SimplePost]]:
        """
        In ASCENDING order of rating. Not descending as you might assume! The
        best posts are at the end of the list so that we can efficiently pop
        them off.
        """
        if len(self._best_posts) >= 1:
            return self._best_posts

        seen = self.dataset.good | self.dataset.bad | self.seen
        self._best_posts = [(self.nbc.predict(i.tags), i)
                            for i in self.dataset.get_all()
                            if i.id not in seen]

        self._best_posts = sorted(self._best_posts, key=lambda x: x[0])

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
        assert not post.deleted
        prediction = self.nbc.predict(post.tags)
        return (prediction, post)

    def get_hot(self) -> Tuple[int, post_data.SimplePost]:
        """
        Posts that have a chance of being good and a chance of being... worse
        than good.
        """
        def post_filter(i):
            rating, post = i
            return rating <= 0

        best_posts = self._get_best_posts()
        best_posts = list(itertools.dropwhile(post_filter, best_posts))
        index = round(random.triangular(0,
                                        len(best_posts)-1,
                                        len(best_posts)-1))

        while index >= 0:
            try:
                result = best_posts.pop(index)
                self.seen.add(result[1].id)
                return result
            except IndexError:
                pass

            index -= 1

        # Can't happen.
        assert False
