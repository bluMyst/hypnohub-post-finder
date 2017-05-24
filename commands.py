import sys

import post_data
import ahto_lib
import hhapi

"""
Takes a command from sys.argv. Basically a low-level CLI frontend to the rest
of my code, for doing things that you can't yet do from HTTP.
"""

# TODO: Everything here should be possible from within the HTTP interface.
#
# Update:
# - How do we keep the user updated on our progress? This command could take a
#   *very* long time to complete. Maybe some sort of realtime link between
#   client and server that's handeled by its own dedicated class?
#
# Reset cache:
# - Easy to do, but be careful! We should have a /misc_controls page, and then
#   an /api/reset_cache page for the Javascript to GET, once we've confirmed
#   that the user knows what they're doing.
#
# Record votes:
# - Figure out how to make an HTML form, and prompt with an ok/cancel popup
#   before doing it. Yattag has some special way of doing forms.
#
# Check deleted:
# - This will require some complex-ish communications between client and
#   server. We might have to store a cookie to know who is who.


class CommandHandler(object):
    def __call__(self, args):
        try:
            script_name, command, *args = args
        except ValueError:
            self.usage(args[0])
            exit(1)

        command = command.lower()

        if not hasattr(self, f'do_{command}'):
            self.usage(script_name)
            exit(1)

        getattr(self, f'do_{command}')(args)

    def usage(self, script_name):
        print("Usage:", script_name, "<command>")
        print()
        print("Possible commands:")

        for i in dir(self):
            if i.startswith("do_"):
                f = getattr(self, i)
                print('-', f.__doc__)

    @ahto_lib.lazy_property
    def dataset(self):
        return post_data.Dataset()

    def do_update(self, args):
        '''update: Update the Hypnohub cache.'''
        self.dataset.update_cache(print_progress=True)
        self.dataset.save()

    def do_reset(self, args):
        '''reset: Clear the Hypnohub cache.'''
        if ahto_lib.yes_no(False, "Reset cache? Are you sure? [yN]"):
            print("Erasing cache...")
            self.dataset.cache = {}
            self.dataset.save()
        else:
            print("Your cache is safe!")

    def do_record_votes(self, args):
        '''record_votes <user>: Add a user's votes to the dataset.'''
        user = args[0]

        if not ahto_lib.yes_no(None, f"Record votes for {user}?"):
            exit(0)

        with ahto_lib.ProgressMapper(2, "Requesting data...") as pm:
            pm(0)
            good_ids  = hhapi.get_vote_data(sys.argv[2], 3)
            pm(1)
            good_ids |= hhapi.get_vote_data(sys.argv[2], 2)

        print("Got", len(good_ids), "items.")

        with ahto_lib.LoadingDone("Saving in cache..."):
            self.dataset.good |= good_ids
            self.dataset.save()

    def do_check_deleted(self, args):
        '''check_deleted: Check if any cached posts have been deleted.'''
        self.dataset.update_cache(print_progress=True)

        for post_id in self.dataset.good | self.dataset.bad:
            if self.dataset.get_id(post_id).deleted:
                yn = ahto_lib.yes_no(
                    False,
                    f"Post #{post_id} appears to be deleted."
                    f" Remove from dataset?")

                if yn:
                    self. dataset.good -= {post_id}
                    self.dataset.bad  -= {post_id}
                    print("Removed")
                else:
                    print("Not removed.")

        with ahto_lib.LoadingDone('Saving...'):
            self.dataset.save()


if __name__ == '__main__':
    ch = CommandHandler()
    ch(sys.argv)
