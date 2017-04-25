import pytest

import post_data
import http_server
import naive_bayes

"""
Tests that don't require us to pester Hypnohub with requests. Ideally almost
all tests should fall under this category.
"""

@pytest.fixture(scope="module")
def dataset():
    return post_data.Dataset()

def test_grup(dataset):
    posts = [post_getters.get_random_uncategorized_post(dataset)
             for i in range(100)]
    assert all(type(post) is post_data.SimplePost for post in posts)

class NaiveBayesTests:
    @pytest.fixture(scope="module")
    def untrained_nbc():
        return naive_bayes.NaiveBayesClassifier()

    @pytest.fixture(scope="module")
    def trained_nbc(dataset):
        return naive_bayes.NaiveBayesClassifier.from_dataset(dataset)

    def test_data(trained_nbc):
        tnbc = trained_nbc
        assert tnbc.ngood <= tnbc.total
        assert tnbc.p_g == tnbc.ngood / tnbc.total

        for k, (good, total) in tnbc.items():
            assert type(k) is str
            assert good <= total
            assert good <= tnbc.ngood
            assert total <= tnbc.total
            assert tnbc.predict(k) >= 0

class PostStorageTests:
    def test_simple_post():
        dummy_json = {
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

        sp = post_data.SimplePost(dummy_json)
        assert not sp.deleted
        assert sp == sp
        assert str(sp).count(dummy_json['id']) == 1
        assert repr(sp).count(dummy_json['id']) == 1

        for k in (set(dummy_json.keys()) - {'id'}):
            temp_json = dummy_json.copy()
            del temp_json[k]
            sp = post_data.SimplePost(temp_json)
            assert sp.deleted
            assert sp.id == dummy_json['id']

    def test_dataset(dataset):
        for k, v in dataset.cache.items():
            assert type(k) is int
            assert type(v) is dict

            spv = dataset.get_id(v)

            assert spv.id == k == int(v.id)
