import random
import math
import pickle
import os

import hypnohub_communication as hhcom

"""
Here's what's going on:

I want to show the user posts based on a Naive Bayes Classifier's best guess
on how they'll like it.

However, the script can also be started in a "training" mode where we'll ask
the user what they think of totally random posts. They can either thumb them
up or thumb them down, and we'll add them to the dataset.

I don't want to have the user vote on stuff that the Classifier is
predicting the user will like, because it seems like we'd start having a
biased dataset.

Speaking of which, this is what the dataset needs to look like: A list of
good posts, by ID and a list of bad posts, by ID. Ideally the tags should be
stored, too.

Also, let's find a way to cache a list of all posts on Hypnohub. Just their
URL's, image URL's, and tags. It's only polite. But every time we start up
this script, it should download data on any new images.

However, we need to make sure that ID's and URL's all stay the same no
matter what. Can probably just ask.  Seems likely, because of all those
"image not found" images we keep getting.
"""

class TestPost(object):
    """ Used to test NaiveBayesClassifier. Please ignore. """
    def __init__(self, tags):
        self.tags = tags

class Dataset(object):
    """ Tracks the posts that the user has liked and disliked. Stores them in a
        file for later use.

        self.raw_dataset = {
            'good': [good_post_ids],
            'bad':  [bad_post_ids],
        }
    """
    FILENAME = "post_preference_data.pickle"

    def __init__(self):
        if os.path.isfile(self.FILENAME):
            with open(self.FILENAME, 'rb') as data_file:
                self.raw_dataset = pickle.load(data_file)
        else:
            self.raw_dataset = {'good':[], 'bad':[]}

    @property
    def good_post_ids(self):
        return self.raw_dataset['good']

    @property
    def bad_post_ids(self):
        return self.raw_dataset['bad']

    def get_good_posts(self):
        return (hhcom.post_cache.get_id(i) for i in self.raw_dataset['good'])

    def get_bad_posts(self):
        return (hhcom.post_cache.get_id(i) for i in self.raw_dataset['bad'])

    def add_good(self, post_id):
        self.raw_dataset['good'].append(int(post_id))

    def add_bad(self, post_id):
        self.raw_dataset['bad'].append(int(post_id))

    def save(self):
        """ Save dataset back to pickle file. """
        with open(self.FILENAME, 'wb') as data_file:
            pickle.dump(self.raw_dataset, data_file)

# There should only ever be one of these, since the data is pickled.
dataset = Dataset()

class NaiveBayesClassifier(object):
    """
        Give it some Post's with tags and it'll try to guess which ones you'll like
        in the future.

        How it works:

        Bayes's Theorem says:

        P(A | B) = P(B | A) * P(A) / P(B)

        Let's say that we want to know how likely someone is to like a certain
        Post.  The best indicator for this is the tags. Let's say that 'G' is
        the statement "this post is good", and 'T0' is the statement "this post
        has tag number 0".

        P(G | T0) = P(T0 | G) * P(G) / P(T0)

        This would work really well if we only had one tag to deal with, but
        let's say there are multiple tags: T0, T1, T2, ...

        I'm going to use the caret (^) symbol in place of the logical AND symbol.

        P(G | T0 ^ T1 ^ ... ^ Tn) = P(T0 ^ T1 ^ ... ^ Tn | G) * P(G) / P(T0 ^ T1 ^ ... ^ Tn)

        Well that won't work at all! P(T0 ^ T1 ^ ...) will only match something
        with exactly identical tags, and we almost definitely don't have
        anything like that in our dataset.

        Let's try something else. Let's intentionally make a bad(ish) assumption
        and say that the tags are conditionally independent. Meaning that a post
        with T0 is just as likely to have T1 as a post without. (P(T0 ^ T1) =
        P(T0 ^ !T1)).  For conditionally independent tags:

        P(X ^ Y | Z) = P(X | Z) * P(Y | Z)

        So let's go back to our multi-tag problem:

        P(G | T0 ^ T1 ^ ... ^ Tn) = P(T0 ^ T1 ^ ... ^ Tn | G) * P(G) / P(T0 ^ T1 ^ ... ^ Tn)

        Let TGP be the "tag is good proportion" of all tags that we're
        interested in combined. This isn't the proportion of good posts that
        have all of the tags. In the vast majority of cases, our data is too
        limited to get anything useful out of a query like that. We might find
        one other post.  Instead, this is an extrapolation based on our
        incomplete data.

        TGP = P(G | T0 ^ T1 ^ ... ^ Tn) = P(T0 | G) * P(T1 | G) * ... * P(Tn | G)

        Let TP be the "has tag proportion" of all tags in all posts we have data
        on.  This is another extrapolation, using the same method as above.

        TP = P(T0 ^ T1 ^ ... ^ Tn) = P(T0) * P(T1) * ... * P(Tn)

        So basically, for a post with tags [T0, T1, ..., Tn]:

        P(G | T0 ^ T1 ^ ... ^ Tn) = TGP * P(G) / TP
    """
    def __init__(self, good_posts, bad_posts):
        self.good_posts = list(good_posts)
        self.bad_posts  = list(bad_posts)

        self.ngood = len(self.good_posts)
        self.total = len(self.bad_posts) + len(self.good_posts)

        self._update_p_g()

        # {'tag_name': [good_posts, total_posts], ...}
        self.tag_history = dict()

    def _update_p_g(self):
        # P(G)
        try:
            self.p_g = self.ngood / self.total
        except ZeroDivisionError:
            # We don't have any posts at all, so we'll default to 50% for each
            # category.
            self.p_g = 0.5

    def add_good(self, post):
        self.good_posts.append(post)
        self.ngood += 1
        self.total += 1
        self._update_p_g()
        self._add_tags(post, True)

    def add_bad(self, post):
        self.bad_posts.append(post)
        self.total += 1
        self._update_p_g()
        self._add_tags(post, False)

    def _add_tags(self, post, is_good):
        for tag in post.tags:
            # self.tag_history looks like this:
            # {'tag_name': [good_posts, total_posts], ...}
            if tag not in self.tag_history:
                self.tag_history[tag] = [0, 0]

            if is_good:
                self.tag_history[tag][0] += 1

            self.tag_history[tag][1] += 1

    def calculate(self):
        for post in self.good_posts:
            self._add_tags(post, True)

        for post in self.bad_posts:
            self._add_tags(post, False)

    def p_t_g(self, tag):
        """
        P(tag | G)

        What's the probability of a good post having this tag?
        """
        try:
            return self.tag_history[tag][0] / self.ngood
        except KeyError:
            return 0
        except ZeroDivisionError:
            # If we don't have any data on good posts.
            if self.total > 0:
                return 0
            else:
                return 0.5

    def p_t(self, tag):
        """
        P(tag)

        What's the probability of any post having this tag?
        """
        try:
            return self.tag_history[tag][1] / self.total
        except KeyError:
            return 0
        except ZeroDivisionError:
            # Just take a wild guess, if we have no dataset to try.
            return 0.01

    def predict(self, post):
        """
        Guess the probability that the user will like a given post, based on
        tags.
        """
        # p(good | tag) = p(tag | good) * p(good) / p(tag)
        tp = 1
        tgp = 1

        for tag in post.tags:
            if tag not in self.tag_history:
                continue

            # TGP *= P(tag | G)
            tgp *= self.p_t_g(tag)

            # TP *= P(tag)
            tp *= self.p_t(tag)

        return tgp * self.p_g / tp

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
