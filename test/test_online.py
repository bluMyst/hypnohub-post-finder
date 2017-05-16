import pytest

import post_data
import hhapi

"""
Tests that are kind of obnoxious, because we have to send requests to Hypnohub
just to get them to work.
"""

# TODO: validate_cache and chunk_validate_cache were copy-pasted here but
# they're not set up to work like unittests yet.
#
# Actually, these shouldn't be unittests. I don't even know why I keep this
# code around anymore. Maybe I should just delete this entire file.

def validate_single_id(id_, print_progress=True):
    post_data = list(hhapi.get_simple_posts("id:" + str(id_)))

    cache_deleted = id_ not in dataset.cache or dataset.get_id(id_).deleted
    post_deleted  = len(post_data) == 0 or post_data[0].deleted

    if len(post_data) < 0 or len(post_data) > 1:
        assert False, ("Something went wrong when trying to communicate "
                       "with Hypnohub and it's probably their fault.",
                       len(post_data))
    elif cache_deleted != post_deleted:
        raise Exception(id_, cache_deleted, post_deleted)

    if id_ not in dataset.cache: return
    assert not dataset.get_id(id_).deleted

    if dataset.get_id(id_) != post_data[0]:
        raise Exception(f"Post #{id_} differs from the cached version.")

def validate_cache(dataset, sample_size=300, print_progress=True):
    """ Make sure there aren't any gaps in the post ID's, except for gaps
    that hypnohub naturally has. (Try searching for "id:8989")

    You can set sample_size to None and it'll check every single post. This
    will obviously take an absurd length of time.
    """

    highest_post = dataset.get_highest_post()

    ids = list(range(1, highest_post+1))

    if sample_size is None or sample_size >= len(ids):
        random.shuffle(ids)
        sample = ids
        sample_size = len(sample)
    else:
        sample = random.sample(ids, sample_size)

    for i, id_ in enumerate(sample):
        if print_progress:
            print('[', i+1, '/', sample_size, ']', sep='', end=' ')
            print('Checking ID#', id_)

        validate_single_id(id_, print_progress)

def chunk_validate_cache(dataset, sample_size=300, print_progress=True):
    # Validate posts by requesting them in chunks of 100.
    # Experimental!
    #
    # NOTE: You need to be a little particular with your search syntax. Here
    # are searches that won't work:
    #
    # id:>=100 id:<=200
    # ~id:1337 ~id:6969 ~id:42
    #
    # And here's a search that will:
    #
    # order:id_desc id:<=300

    # Find the highest post id and split it into chunks of 100, then create a
    # final chunk of however many are left. Store each chunk as a number: the
    # highest id in that chunk. ID's start at 1, so the highest in each chunk
    # will be 100*chunk_number. Except for the last chunk, of course.
    # Example: [
    #     100,
    #     200,
    #     236
    # ]
    highest_post            = dataset.get_highest_post()
    num_chunks              = math.ceil(highest_post / 100)
    last_chunk_size         = highest_post % 100
    second_last_chunk_value = highest_post - (highest_post % 100)

    chunks = list(range(100, second_last_chunk_value+1, 100))
    chunks.append(highest_post)
    assert num_chunks == len(chunks)

    if len(chunks) > sample_size:
        chunks = random.sample(chunks, 300)

    for last_id_in_chunk in chunks:
        if print_progress:
            print(f'{last_id_in_chunk-99}-{last_id_in_chunk}/{highest_post}')

        posts = list(
            hhapi.get_simple_posts(f'id:<={last_id_in_chunk} order:id_desc'))

        assert len(posts) <= 100, (last_id_in_chunk, len(chunks),
                chunks.index(last_id_in_chunk))

        for post in posts:
            assert post.id in range(last_id_in_chunk-99, last_id_in_chunk+1), (
                    post.id)

            cached_post = dataset.get_id(post.id)

            assert cached_post.deleted == post.deleted, post.id

            if not post.deleted:
                assert post == cached_post, (str(post), str(cached_post))
