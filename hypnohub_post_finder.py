import sys
import configparser

import ahto_lib
import post_rater
import http_server
import hypnohub_communication as hhcom

cfg = configparser.ConfigParser()
cfg.read('config.cfg')

def usage():
    print("Usage:", sys.argv[0], "<posts to get>")

if __name__ == '__main__':
    try:
        with open('start_id.txt', 'r') as f:
            start_id = int(f.read())

        print("start_id.txt ->", start_id)
    except IOError:
        start_id = 0

        with open('start_id.txt', 'w') as f:
            f.write(str(start_id))

        print("No start_id.txt. Created as " + str(start_id) + ".")

    try:
        posts_to_get = int(sys.argv[1])
    except IndexError:
        posts_to_get = cfg['General'].getint('Default Posts to Get')
    except ValueError:
        usage()
        exit(1)

    post_getter = hhcom.PostGetter(start_id)
    good_posts = post_getter.get_n_good_posts(posts_to_get)

    html_generator.posts_to_browser(good_posts)

    next_post_id = str(post_getter.highest_id + 1)

    response = ahto_lib.yes_no(True, "Next unseen post is {next_post_id}. Save"
        " your progress?".format(**locals()))

    if response:
        with open('start_id.txt', 'w') as f:
            f.write(next_post_id)

        print('Written.')
    else:
        print('Not written.')
