import random
import math
from typing import List

import post_data

class NaiveBayesClassifier(object):
    """
    Give it some Post's with tags and it'll try to guess which ones you'll like
    in the future.

    Don't expect this class to always have predictions <= 1.0. The naive
    assumption fucks with the numbers a lot and it can get crazy high.

    How it works:

    Well first of all, let's talk about syntax. Math is INCREDIBLY hard to do
    in UTF-8, or really any computerized format, so I'm just going to make some
    stuff up:

    syntax         | meaning
    P(A)           | The probability of statement 'A' being true.
    P(A|B)         | The probability of 'A' being true, assuming 'B' is true.
    A&B            | A and B
    pi{i=0->5}(i)  | The pi notation of i=0 to 5, multiplying i. In other
                   | words: 0*1*2*3*4*5

    Bayes's Theorem says, given evidence E and a state we're interested in S:

    P(S|E) = P(E|S) * P(S) / P(E)

    Let's say that we want to know how likely someone is to like a certain
    Post. The best indicator for this is the tags. Let's say that 'G' is
    the statement "this post is good", and 'T0' is the statement "this post
    has tag number 0".

    P(G| 0) = P(T0|G) * P(G) / P(T0)

    This would work really well if we only had one tag to deal with, but
    let's say we're looking at a Post with "n" tags: T0, T1, T2, ..., Tn

    Ta = pi{i=0->n}(Tn)
    P(G|Ta) = P(Ta|G) * P(G) / P(Ta)

    Well that won't work at all! P(Ta) will only match something
    with exactly identical tags, and we almost definitely don't have
    anything like /that/ in our dataset.

    Let's try something else. Let's intentionally make a bad(ish) assumption
    and say that the tags are conditionally independent. Meaning that a post
    with T0 is just as likely to have T1 as a post without. In other words,
    let's assume:

    P(T0|T1) = P(T0|!T1)

    Why are we making this assumption? Because for conditionally independent
    tags:

    P(X&Y|Z) = P(X|Z) * P(Y|Z)
    P(X&Y)   = P(X) * P(Y)

    So let's go back to our multi-tag problem:

    P(G|Ta) = P(Ta|G) * P(G) / P(Ta)
    P(G|Ta) = P(G) * P(Ta|G) / P(Ta)

    Make sense? I hope so! Anyway, we can simplify the above equation down to:

    P(G | Ta) = P(G) * pi{i=0->n}( P(Ti | G) / P(Ti) )

    Now check out this pseudocode:

    answer = P(G)
    for tag in tags:
        answer *= P(tag | G) / P(tag)

    That's all it takes!
    """

    def __init__(self, good_posts: List[List[str]],
                 bad_posts: List[List[str]]):
        good_posts, bad_posts = list(good_posts), list(bad_posts)

        self.ngood = len(good_posts)
        self.total = len(bad_posts) + len(good_posts)

        try:
            self.p_g = self.ngood / self.total
        except ZeroDivisionError:
            self.p_g = None

        # {'tag_name': [n_good_posts, n_total_posts], ...}
        self.tag_history = dict()

        for post in good_posts:
            self._add_tags(post, True)

        for post in bad_posts:
            self._add_tags(post, False)

    @classmethod
    def from_dataset(cls, dataset: post_data.Dataset, *args, **kwargs):
        """ Alternative constructor. All * and ** args passed to __init__"""
        good_posts = [i.tags for i in dataset.get_good() if hasattr(i, 'tags')]
        bad_posts  = [i.tags for i in dataset.get_bad()  if hasattr(i, 'tags')]

        return cls(good_posts, bad_posts, *args, **kwargs)

    def _add_tags(self, post: List[str], is_good: bool):
        for tag in post:
            if tag not in self.tag_history:
                self.tag_history[tag] = [0, 0]

            if is_good:
                self.tag_history[tag][0] += 1

            self.tag_history[tag][1] += 1

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

    def single_tag_predict(self, tag, p_g=None):
        if p_g is None:
            p_g = self.p_g

        if tag not in self.tag_history:
            return p_g

        return p_g * self.p_t_g(tag) / self.p_t(tag)

    def predict(self, post: List[str]):
        """
        Guess the probability that the user will like a given post, based on
        tags.
        """
        temp = self.p_g

        for tag in post:
            temp = self.single_tag_predict(tag, temp)

        return temp
