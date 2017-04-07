import requests
import bs4
import pickle

import hypnohub_communication as hhcom

if __name__ == '__main__':
    pc = hhcom.PostCache()
    pc.update_cache(True)
    old_len = len(pc.all_posts)
    pc.save_cache()

    pc = hhcom.PostCache()
    assert len(pc.all_posts) == old_len
    pc.validate_data(None, True)

#if __name__ == '__main__':
#    pc = hhcom.PostCache()
#    pc.update_cache(True)
#    pc.save_cache()
#    pc.validate_data(print_progress=True)
#
#    pc2 = hhcom.PostCache()
#    pc2.validate_data(print_progress=True)
#    assert len(pc.all_posts) == len(pc2.all_posts)
#
#    for i, j in zip(pc.all_posts.values(), pc2.all_posts.values()):
#        assert (i is None and j is None) or i.id == j.id, str(i) + ' != ' + str(j)
#    pass
