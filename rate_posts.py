import webbrowser

import hypnohub_communication as hhcom
import naive_bayes
import post_data

def get_random_uncategorized_post():
    """ Get a random post from the cache that has yet to be categorized
        into either 'good' or 'bad'.
    """
    randomly_sorted_posts = [
        i for i in post_data.dataset.all_posts.values()
        if i.id not in self.good and i.id not in self.bad]

    return random.choice(randomly_sorted_posts)

if __name__ == '__main__':
    classifier = naive_bayes.NaiveBayesClassifier(
        post_data.dataset.get_good(),
        post_data.dataset.get_bad())

    try:
        while True:
            random_post = get_random_uncategorized_post()
            webbrowser.open(random_post.page_url)

            while True:
                like = input("Do you like it? [y/n]").lower()

                if like in 'yn':
                    break

                print("Invalid input:", like)

            rating_before = classifier.predict(random_post, debug=True)

            print('-'*80)

            if like == 'y':
                post_data.dataset.add_good(random_post.id)
                classifier.add_good(random_post)
                print("Adding post ID#", random_post.id,
                    'to list of good posts.')
            else:
                post_data.dataset.add_bad(random_post.id)
                classifier.add_bad(random_post)
                print("Adding post ID#", random_post.id,
                    'to list of bad posts.')

            print('-'*80)

            print("NaiveBayseClassifier rating:", rating_before, "(before)",
                  classifier.predict(random_post, debug=True), "(after)")
            print()

            if input("Press enter for next post or [q]uit.").lower() == 'q':
                break
    except KeyboardInterrupt:
        pass

    print("Saving dataset to pickle file...", end=' ')
    post_data.dataset.save()
    print("done.")
