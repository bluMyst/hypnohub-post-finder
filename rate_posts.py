import webbrowser

import hypnohub_communication as hhcom
import naive_bayes

if __name__ == '__main__':
    classifier = naive_bayes.NaiveBayesClassifier(
        naive_bayes.dataset.get_good_posts(),
        naive_bayes.dataset.get_bad_posts())

    try:
        while True:
            random_post = hhcom.post_cache.get_random_post()
            webbrowser.open(random_post.page_url)

            while True:
                like = input("Do you like it? [y/n]").lower()

                if like in 'yn':
                    break

                print("Invalid input:", like)

            rating_before = classifier.predict(random_post, debug=True)

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
                  classifier.predict(random_post, debug=True), "(after)")
            print()

            if input("Press enter for next post or [q]uit.").lower() == 'q':
                break
    except KeyboardInterrupt:
        pass

    #print("Saving dataset to pickle file...")
    #naive_bayes.dataset.save()
