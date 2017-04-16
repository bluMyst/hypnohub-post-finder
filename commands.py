import sys

import post_data
import naive_bayes
import http_server

"""
Takes a command from sys.argv. Basically a low-level CLI frontend to the rest
of my code, for doing things that you can't yet do from HTTP.
"""

def usage():
    print("Usage:", sys.argv[0], "<command>")
    print()
    print("Possible commands:",
          "- u[pdate]: update cache",
          "- v[alidate] [sample_size=300]: validate up to sample_size cache items",
          "- s[erve]: start serving http.",
          "- v[otes]: show your current vote data",
          "- r[eset_cache]: remove everything from the cache",
          "- n[aive_debug]: show some data on the naive bayes classifier",
          sep='\n')

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
        exit(1)

    command = sys.argv[1].lower()

    if command in ['u', 'update']:
        dataset = post_data.Dataset()
        dataset.update_cache(print_progress=True)
        dataset.save()
    elif command in ['v', 'validate']:
        try:
            sample_size = int(sys.argv[2])
        except ValueError:
            usage()
            exit(1)
        except IndexError:
            post_data.validate_cache(print_progress=True)
        else:
            post_data.validate_cache(sample_size, print_progress=True)
    elif command in ['s', 'serve']:
        server_address = ('127.0.0.1', 8000)
        print("Serving on:",
              f"http://{server_address[0]}:{server_address[1]}/")
        try:
            handler = http_server.RecommendationRequestHandler(server_address)
            handler.server.serve_forever()
        except KeyboardInterrupt:
            pass
        else:
            exit(1) # Just in case .serve_forever() fails somehow.
    elif command in ['v', 'votes']:
        dataset = post_data.Dataset()
        print("Good:", dataset.good)
        print("Bad:", dataset.bad)
    elif command in ['r', 'reset_cache']:
        dataset = post_data.Dataset()

        if input("Reset cache? Are you sure? [yN]").lower() != 'y':
            print("Your cache is safe!")
            exit(0)

        print("Erasing cache...")
        dataset.cache = {}
        dataset.save()
    elif command in ['n', 'naive_show']:
        nbc = naive_bayes.NaiveBayesClassifier.from_dataset(post_data.Dataset())

        for tag, (good, total) in list(nbc.tag_history.items())[-100:]:
            predict = nbc.predict([tag])

            if predict > 0:
                print(f"----------{tag} ({good}/{total})----------")

                print(f"P(T|G) = {good} / {nbc.ngood} = {nbc.p_t_g(tag):.2%}")
                print(f"P(G)   = {nbc.ngood} / {nbc.total} = {nbc.p_g:.2%}")
                print(f"P(T)   = {total} / {nbc.total} = {nbc.p_t(tag):.2%}")
                print()
                print(f"P(G|T) = {predict:.2%}")
                print()
    else:
        usage()
        exit(1)
