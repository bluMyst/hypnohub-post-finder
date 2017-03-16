import random
import math

class TestPost(object):
    """ Used to test NaiveBayesClassifier. Please ignore. """
    def __init__(self, tags):
        self.tags = tags

class NaiveBayesClassifier(object):
    """
    Give it some Post's with tags and it'll try to guess which ones you'll like
    in the future.

    How it works:

    Bayes's Theorem says:

    P(A | B) = P(B | A) * P(A) / P(B)

    Let's say that we want to know how likely someone is to like a certain Post.
    The best indicator for this is the tags. Let's say that 'G' is the statement
    "this post is good", and 'T0' is the statement "this post has tag number 0".

    P(G | T0) = P(T0 | G) * P(G) / P(T0)

    This would work really well if we only had one tag to deal with, but let's
    say there are multiple tags: T0, T1, T2, ...

    I'm going to use the caret (^) symbol in place of the logical AND symbol.

    P(G | T0 ^ T1 ^ ...) = P(T0 ^ T1 ^ ... | G) * P(G) / P(T0 ^ T1 ^ ...)

    Well that won't work at all! P(T0 ^ T1 ^ ...) will only match something with
    exactly identical tags, and we almost definitely don't have anything like
    that in our dataset.

    Let's try something else. Let's intentionally make a bad(ish) assumption and
    say that the tags are conditionally independent. Meaning that a post with T0
    is just as likely to have T1 as a post without. (P(T0 ^ T1) = P(T0 ^ !T1)).
    For conditionally independent tags:

    P(X ^ Y | Z) = P(X | Z) * P(Y | Z)

    So let's go back to our multi-tag problem:

    P(G | T0 ^ T1) = P(T0 ^ T1 | G) * P(G) / P(T0 ^ T1)
    P(G | T0 ^ T1) = P(T0 | G) * P(T1 | G) * P(G) / P(T0) * P(T1)

    ------------------------------ CONTINUE LATER ------------------------------
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
