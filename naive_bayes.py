import random
import math
import pickle
import os
import abc
from typing import *

import hypnohub_communication as hhcom
import post_data

""" Here's what's going on:

I want to show the user posts based on a Naive Bayes Classifier's best guess
on how they'll like it.

However, the script can also be started in a "training" mode where we'll ask
the user what they think of totally random posts. They can either thumb them
up or thumb them down, and we'll add them to the dataset.

I don't want to have the user vote on stuff that the Classifier is
predicting the user will like, because it seems like we'd start having a
biased dataset. We should find out for sure, though.

We need to make sure that ID's all stay the same no matter what. Can probably
just ask. Seems likely, because of all those deleted posts and blank spots in
the ID list.
"""

class NaiveBayesClassifier(object):
    """
    Give it some Post's with tags and it'll try to guess which ones you'll like
    in the future.

    How it works:

    Bayes's Theorem says, given evidence E and a state we're interested in S:

    P(S | E) = P(E | S) * P(S) / P(E)

    Let's say that we want to know how likely someone is to like a certain
    Post. The best indicator for this is the tags. Let's say that 'G' is
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
    with T0 is just as likely to have T1 as a post without. (P(T0 | T1) =
    P(T0 | !T1)).  For conditionally independent tags:

    P(X ^ Y | Z) = P(X | Z) * P(Y | Z)

    So let's go back to our multi-tag problem:

    P(G | T0 ^ T1 ^ ... ^ Tn) = P(T0 ^ T1 ^ ... ^ Tn | G) * P(G) / P(T0 ^ T1 ^ ... ^ Tn)

    Let TGP be the "tag is good proportion" of all tags that we're
    interested in combined. This isn't the proportion of good posts that
    have all of the tags. In the vast majority of cases, our data is too
    limited to get anything useful out of a query like that. We might find
    one other post. Instead, this is an extrapolation based on our
    incomplete data.

    TGP = P(T0 ^ T1 ^ ... ^ Tn | G) = P(T0 | G) * P(T1 | G) * ... * P(Tn | G)

    Let TP be the "has tag proportion" of all tags in all posts we have data
    on. This is another extrapolation, using the same method as above.

    TP = P(T0 ^ T1 ^ ... ^ Tn) = P(T0) * P(T1) * ... * P(Tn)

    So basically, for a post with tags [T0, T1, ..., Tn]:

    P(G | T0 ^ T1 ^ ... ^ Tn) = TGP * P(G) / TP
    """
    # TODO: I did something wrong, here. TP gets insanely small which causes
    # predict() to output super high numbers.
    #
    # EDIT: What the fuuuuuucckkk!
    # Loading cache... done.
    # P(T|G) = 0.75
    # P(T)   = 0.8108108108108109
    # femsub : tgp *= 0.9249999999999999 : 0.9249999999999999
    # P(T|G) = 0.25
    # P(T)   = 0.3783783783783784
    # text : tgp *= 0.6607142857142857 : 0.6111607142857143
    # P(T|G) = 0.25
    # P(T)   = 0.013513513513513514
    # diaper : tgp *= 18.5 : 11.306473214285715
    # P(T|G) = 0.25
    # P(T)   = 0.14864864864864866
    # femdom : tgp *= 1.6818181818181817 : 19.01543222402597
    # 1.0278612012987012 #40237 +9 by Sleepyhead97
    # PS> python
    # Python 3.6.1 (v3.6.1:69c0db5, Mar 21 2017, 17:54:52) [MSC v.1900 32 bit (Intel)] on win32
    # Type "help", "copyright", "credits" or "license" for more information.
    # >>> import naive_bayes
    # >>> nbc = naive_bayes.naive_bayes_classifier
    # >>> nbc.tag_history['diaper']
    # [1, 1]
    # >>> nbc.p_t('diaper')
    # 0.013513513513513514
    # >>> nbc.p_t_g('diaper')
    # 0.25
    # >>> nbc.ngood
    # 4
    # >>> nbc.p_g
    # 0.05405405405405406
    # >>> nbc.p_t_g('diaper') / nbc.p_t('diaper')
    # 18.5
    # >>> _ * nbc.p_g
    # 1.0
    # >>> exit()
    def __init__(self, good_posts: List[List[str]], bad_posts: List[List[str]],
            auto_calculate=True):
        self.good_posts = list(good_posts)
        self.bad_posts  = list(bad_posts)

        self.ngood = len(self.good_posts)
        self.total = len(self.bad_posts) + len(self.good_posts)

        self._update_p_g()

        # {'tag_name': [good_posts, total_posts], ...}
        self.tag_history = dict()

        if auto_calculate:
            self.calculate()

    def _update_p_g(self):
        # P(G)
        try:
            self.p_g = self.ngood / self.total
        except ZeroDivisionError:
            # We don't have any posts at all, so we'll default to 50% for each
            # category.
            self.p_g = 0.5

    def add_good(self, post: List[str]):
        self.good_posts.append(post)
        self.ngood += 1
        self.total += 1
        self._update_p_g()
        self._add_tags(post, True)

    def add_bad(self, post:List[str]):
        self.bad_posts.append(post)
        self.total += 1
        self._update_p_g()
        self._add_tags(post, False)

    def _add_tags(self, post: List[str], is_good: bool):
        for tag in post:
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

        What's the probability of this tag existing in a random good post?
        """
        try:
            return self.tag_history[tag][0] / self.ngood
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
        except ZeroDivisionError:
            # Just take a wild guess, if we have no dataset to try.
            return 0.01

    def predict(self, post: List[str], debug=False):
        """
        Guess the probability that the user will like a given post, based on
        tags.
        """
        temp = 1

        for tag in post:
            if tag not in self.tag_history:
                continue

            temp *= self.p_t_g(tag) / self.p_t(tag)

            if debug:
                print("P(T|G) =", self.p_t_g(tag))
                print("P(T)   =", self.p_t(tag))
                print(tag, ": temp *=", self.p_t_g(tag) / self.p_t(tag), ':', temp)

        return temp * self.p_g

good_tags = [i.tags for i in post_data.dataset.get_good()]
bad_tags  = [i.tags for i in post_data.dataset.get_bad()]
naive_bayes_classifier = NaiveBayesClassifier(good_tags, bad_tags)
del good_tags, bad_tags

def split_dataset(dataset, split_ratio=0.33):
    """
    Split a dataset between data used for training and data used for testing
    the algorithm after training is complete.

    Split ratio: What portion is used for training data?
    """
    # I definitely won't be using this as-is, but it's nice to have as a
    # reference for later.
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
