import sys

import post_data
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
          sep='\n')

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
        exit(1)

    command = sys.argv[1].lower()

    if command in ['u', 'update']:
        post_data.dataset.update_cache(print_progress=True)
        post_data.dataset.save()
        exit(0)
    elif command in ['v', 'validate']:
        try:
            sample_size = int(sys.argv[2])
        except ValueError:
            usage()
            exit(1)
        except IndexError:
            post_data.validate_cache(print_progress=True)
            exit(0)

        post_data.validate_cache(sample_size, print_progress=True)
        exit(0)
    elif command in ['s', 'serve']:
        server_address = ('127.0.0.1', 8000)
        print("Serving on:",
              "http://" + server_address[0] + ':' + str(server_address[1]) + '/')
        try:
            handler = http_server.RecommendationRequestHandler(server_address)
            handler.server.serve_forever()
        except KeyboardInterrupt:
            exit(0)

        exit(1) # Shouldn't ever be called.
    elif command in ['v', 'votes']:
        print("Good:", post_data.dataset.good)
        print("Bad:", post_data.dataset.bad)
        exit(0)
    elif command in ['r', 'reset_cache']:
        post_data.dataset.cache = {}
        post_data.dataset.save()
    else:
        usage()
        exit(1)
