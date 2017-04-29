import pytest
import itertools

import post_data
import http_server
import naive_bayes
import ahto_lib
import post_getters

"""
Tests that don't require us to pester Hypnohub with requests. Ideally almost all
tests should fall under this category.
"""

@pytest.fixture(scope="module")
def dataset():
    return post_data.Dataset()

@pytest.fixture(scope="module")
def untrained_nbc():
    return naive_bayes.NaiveBayesClassifier()

@pytest.fixture(scope="module")
def trained_nbc(dataset):
    return naive_bayes.NaiveBayesClassifier.from_dataset(dataset)

def test_grup(dataset):
    posts = [post_getters.get_random_uncategorized_post(dataset)
             for i in range(10)]
    assert all((type(post) is post_data.SimplePost
               and post.id not in dataset.good & dataset.bad)
               for post in posts)

class TestNaiveBayes:
    def test_tnbc_sanity(self, trained_nbc):
        tnbc = trained_nbc
        assert tnbc.ngood <= tnbc.total
        assert tnbc.p_g == tnbc.ngood / tnbc.total

    def test_tnbc_items(self, trained_nbc):
        tnbc = trained_nbc
        items = tnbc.good_posts.items() | tnbc.bad_posts.items()

        for tag_name, (good, total) in items:
            assert type(tag_name) is str
            assert good <= total
            assert good <= tnbc.ngood
            assert total <= tnbc.total
            assert tnbc.predict(tag_name) >= 0

DUMMY_JSON = {
    'id': 1337,
    'score': '1338',
    'rating': 's',
    'tags': 'foo bar baz',
    'author': "foo",
    'md5': 'deadbeefc0fe',
    'file_url':    '//hypnohub.net//data/image/deadbeefc0fe.jpg',
    'jpeg_url':    '//hypnohub.net//data/image/deadbeefc0fe.jpg',
    'preview_url': '//hypnohub.net//data/preview/deadbeefc0fe.jpg',
    'sample_url':  '//hypnohub.net//data/sample/deadbeefc0fe.jpg',
}

class TestPostStorage:
    def test_simple_post(self):
        sp = post_data.SimplePost(DUMMY_JSON)
        assert not sp.deleted
        assert sp == sp

        id_ = str(DUMMY_JSON['id'])
        assert str(sp).count(id_) == 1
        assert repr(sp).count(id_) == 1

        # List[Tuple[str]]
        keys_to_delete = ahto_lib.any_length_permutation(
                DUMMY_JSON.keys() - {'id'})
        for keys in keys_to_delete:
            temp_json = DUMMY_JSON.copy()

            for key in keys: del temp_json[key]

            sp = post_data.SimplePost(temp_json)
            assert sp.deleted
            assert sp.id == DUMMY_JSON['id']

    def test_dataset(self, dataset):
        for k, v in dataset.cache.items():
            assert type(k) is int
            assert type(v) is dict

            spv = dataset.get_id(v)

            assert spv.id == k == int(v.id)
