import sys
import warnings

import post_data
import naive_bayes
import http_server
import ahto_lib
import hypnohub_communication as hhcom

"""
Takes a command from sys.argv. Basically a low-level CLI frontend to the rest
of my code, for doing things that you can't yet do from HTTP.
"""

# TODO: Everything here should be possible from within the HTTP interface.
# Except, obviously, the "serve" command which should be its own file. Probably
# called "run" or something.

def usage():
    print("Usage:", sys.argv[0], "<command>")
    print()
    print("Possible commands:",
          "- u[pdate]: update cache",
          "- v[alidate] [sample_size=300]: validate up to sample_size cache"
             " items",
          "- r[eset_cache]: remove everything from the cache",
          "- re[cord_votes] <user>: get the likes and favorites from <user> and"
             " add them to dataset.good.",
          "- c[heck_deleted]: check to see if any of the dataset id's have been"
             " deleted.",
          sep='\n')

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
        exit(1)

    command = sys.argv[1].lower()

    if command in ['u', 'update']:
        with warnings.catch_warnings():
            dataset = post_data.Dataset()

        dataset.update_cache(print_progress=True)
        dataset.save()
    elif command in ['v', 'validate']:
        dataset = post_data.Dataset()

        try:
            sample_size = int(sys.argv[2])
        except ValueError:
            usage()
            exit(1)
        except IndexError:
            post_data.validate_cache(dataset, print_progress=True)
        else:
            post_data.validate_cache(dataset, sample_size, print_progress=True)
    elif command in ['v', 'votes']:
        dataset = post_data.Dataset()
        print("Good:", dataset.good)
        print("Bad:", dataset.bad)
    elif command in ['r', 'reset_cache']:
        dataset = post_data.Dataset()

        if ahto_lib.yes_no(False, "Reset cache? Are you sure? [yN]"):
            print("Erasing cache...")
            dataset.cache = {}
            dataset.save()
        else:
            print("Your cache is safe!")
    elif command in ['re', 'record_votes']:
        dataset = post_data.Dataset()

        user = sys.argv[2]

        while True:
            yn = input(f"Record votes for {user}? [yn]").lower()

            if yn == 'y':
                break
            elif yn == 'n':
                exit(0)

        with ahto_lib.ProgressMapper(2, "Requesting data...") as pm:
            pm(0)
            good_ids  = hhcom.get_vote_data(sys.argv[2], 3)
            pm(1)
            good_ids |= hhcom.get_vote_data(sys.argv[2], 2)

        print("Got", len(good_ids), "items.")
        print("Saving in cache...", end=' ')
        dataset.good |= good_ids
        dataset.save()
        print("done.")
    elif command in ['ch', 'check_deleted']:
        with ahto_lib.LoadingDone("Loading dataset..."):
            with warnings.catch_warnings():
                dataset = post_data.Dataset()

        dataset.update_cache(print_progress=True)

        for post_id in dataset.good | dataset.bad:
            if dataset.get_id(post_id).deleted:
                if ahto_lib.yes_no(False,
                                   f"Post #{post_id} appears to be deleted."
                                   f" Remove from dataset?"):
                    dataset.good -= {post_id}
                    dataset.bad  -= {post_id}
                    print("Removed")
                else:
                    print("Not removed.")

        print("Saving...", end=' ')
        dataset.save()
        print("done.")
    else:
        usage()
        exit(1)
