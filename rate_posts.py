import random
import webbrowser

import hypnohub_communication as hhcom
import naive_bayes

def get_random_existant_post():
    randomly_sorted_posts = list(i for i in hhcom.post_cache.all_posts.values())
    random.shuffle(randomly_sorted_posts)

    for post in randomly_sorted_posts:
        if post is not None:
            return post

if __name__ == '__main__':
    good_posts = naive_bayes.dataset.get_good_posts()
    bad_posts  = naive_bayes.dataset.get_bad_posts()
    classifier = naive_bayes.NaiveBayesClassifier(good_posts, bad_posts)

    try:
        while True:
            if input("Press enter for next post or [q]uit.").lower() == 'q':
                break

            random_post = get_random_existant_post()
            webbrowser.open(random_post.page_url)

            while True:
                like = input("Do you like it? [y/n]").lower()

                if like in 'yn':
                    break

                print("Invalid input:", like)

            rating_before = classifier.predict(random_post)

            if like == 'y':
                naive_bayes.dataset.add_good(random_post.id)
                classifier.add_good(random_post)
                print("Adding post ID#", random_post.id,
                    'to list of good posts.')
            else:
                naive_bayes.dataset.add_bad(random_post.id)
                classifier.add_bad(random_post)
                print("Adding post ID#", random_post.id,
                    'to list of bad posts.')

            print("NaiveBayseClassifier rating:", rating_before, "(before)",
                  classifier.predict(random_post), "(after)")
            print()
    except KeyboardInterrupt:
        pass

    print("Saving dataset to pickle file...")
    naive_bayes.dataset.save()
