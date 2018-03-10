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
    in plain text, so I'm just going to make some stuff up:

    syntax         | meaning
    P(A)           | The probability of statement 'A' being true.
    P(A|B)         | The probability of 'A' being true, assuming 'B' is true.
    N()            | The number of posts
    N(V)           | The number of posts voted on (up or down) by the user
    N(U)           | The number of posts upvoted by the user
    N(U, T0)       | Same as above, but they also have a tag that we're calling
                   | tag 0 for convenience. (will make more sense later)
    A&B            | A and B
    pi{i=0->5}(i)  | The pi notation of i=0 to 5, multiplying i. In other
                   | words: 0*1*2*3*4*5

    This is Bayes' Theorem:

    P(A|B) = P(B|A) * P(A) / P(B)

    But what does that actually mean? Well, Bayes' Theorem is a way of
    computing how likely something is to be true, given a list of evidence. For
    example, let's say we want to guess the probability that someone will think
    a Hypnohub post is good. We'll call that "P(G)". To do this, we'll look at
    the tags of the post (T = T[0], T[1], T[2], ... T[N]). Bayes' Theorem tells
    us that we can calculate the answer like so:

    P(G|T) = P(T|G) * P(G) / P(T)

    The probability that a user will like a given post, if all we know about it
    is the tags, is equal to the probability that a good post would have
    identical tags, multiplied by the probability that any random post is good,
    divided by the probability of any random post having identical tags.

    So far, this equation seems pretty useless. After all, how are we supposed
    to figure out P(T|G), or even P(T)? There are so many possible tags that a
    post can have, that the odds of finding even a single other post with
    matching tags is pretty much 0. Well, there's actually a way to fudge these
    two numbers, that I'll get to later. For now, let's look at a simpler
    example.

    Let's say that we've found the only post on Hypnohub with a single tag.
    Every other post has a normal number of tags, but this one has only one.
    We can calculate the probability that the user will like it like so:

    P(G|T0) = P(T0|G) * P(G) / P(T0)

    But how do we calculate all these values? Well, it's actually pretty easy!

    P(T0|G) is equal to the probability that a post with T0 is good. To find
    this, we just have to take the number of posts with T0 that the user has
    upvoted, and divide by the total number of posts with T0 that the user has
    voted on:

    P(T0|G) = num upvoted with T0 / num voted on with T0
    P(T0|G) = N(U, T0) / N(T0)

    P(G) is even easier! It's equal to the total number of posts the user has
    upvoted, divided by the total number of posts the user has voted on.

    P(G) = num upvoted / num voted on
    P(G) = N(U) / N(V)

    And for P(T0), all you have to do is find the number of cached posts with
    T0, and divide by the total number of cached posts.

    P(T0) = num posts with T0 / num posts
    P(T0) = N(T0) / N()

    TODO: Stopped rewording here, but need to continue.

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
