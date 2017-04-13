import sys

import post_data

"""
Takes a command from sys.argv. Basically a low-level CLI frontend to the rest
of my code, for doing things that you can't yet do from HTTP.
"""

def usage():
    print("Usage:", sys.argv[0], "<command>")
    print()
    print("Possible commands:",
          "- u[pdate]: update post_data.dataset",
          "- v[alidate] <sample_size>: validate up to sample_size cache items",
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
    else:
        usage()
        exit(1)
