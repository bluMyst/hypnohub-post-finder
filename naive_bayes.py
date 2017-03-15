import random
import math

class TestPost(object):
    """ Used to test NaiveBayesClassifier. Please ignore. """
    def __init__(self, tags):
        self.tags = tags

class NaiveBayesClassifier(object):
    """
    Give it some Post's with tags and it'll try to guess which ones you'll like in the future.
    """
    def __init__(self, good_posts, bad_posts):
        self.good_posts = list(good_posts)
        self.bad_posts  = list(bad_posts)

        self.ngood = len(self.good_posts)
        self.total = len(self.bad_posts) + len(self.good_posts)

        # p(good post) given no information about it
        self.p_good = self.ngood / self.total

        # {'tag_name': [good_posts, total_posts], ...}
        self.tag_history = dict()

    def calculate(self):
        def count_tag_ratings(posts, is_good):
            for post in posts:
                for tag in post.tags:
                    # self.tag_history looks like this:
                    # {'tag_name': [good_posts, bad_posts], ...}
                    # So target_index gives the index of either good_posts or
                    # bad_posts.
                    if tag not in self.tag_history:
                        self.tag_history[tag] = [0, 0]

                    if is_good:
                        self.tag_history[tag][0] += 1

                    self.tag_history[tag][1] += 1

        count_tag_ratings(self.good_posts, True)
        count_tag_ratings(self.bad_posts,  False)

    def predict(self, post):
        """
        Guess the probability that the user will like a given post, based on tags.
        """
        # p(good | tag) = p(tag | good) * p(good) / p(tag)
        p_good = self.p_good

        for tag in post.tags:
            if tag not in self.tag_history:
                continue

            # p(good) *= p(tag | good)
            p_good *= self.tag_history[tag][0] / self.ngood

            # p(good) /= p(tag)
            p_good /= self.tag_history[tag][1] / self.total

        return p_good

def split_dataset(dataset, split_ratio=0.33):
    """
    Split a dataset between data used for training and data used for testing
    the algorithm after training is complete.

    Split ratio: What portion is used for training data?
    """
    train_size = math.round(len(dataset) * split_ratio)

    copy = dataset[:]
    random.shuffle(copy)
    train_set = copy[:train_size]
    test_set  = copy[train_size:]

    return train_set, test_set

if __name__ == '__main__':
    good_posts = [
        ['foo', 'bar'],
        ['bar'],
        ['foo', 'quux']
    ]

    bad_posts = [
        ['bar', 'qux'],
        ['bar'],
        ['qux']
    ]

    bad_posts = map(TestPost, bad_posts)
    good_posts = map(TestPost, good_posts)

    nbc = NaiveBayesClassifier(good_posts, bad_posts)
    nbc.calculate()
