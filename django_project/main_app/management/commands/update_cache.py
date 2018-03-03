import queue
import itertools

from django.core.management.base import BaseCommand, CommandError

from main_app.hhapi import HypnohubAPIRequester
from main_app.models import Post

class Command(BaseCommand):
    help = "Updates the local database of Post's to match Hypnohub."

    def save_all_posts(self, posts):
        """
        Returns a tuple: (made_progress, temporary_orphans)

        temporary_orphans: A list of temporary orphans, sorted by id.

        made_progress: Whether any of the supplied posts were successfully
                       saved.

        Every post not returned as an orphan has been saved.
        """
        temporary_orphans = []
        made_progress = False

        for i, post in enumerate(posts):
            try:
                sqlfied_post = Post.from_json(post)
            except Post.DoesNotExist:
                self.stdout.write(self.style.NOTICE(
                    f"Setting aside a temporarily orphaned post: "
                    f"{post['id']} with parent {post['parent']}"
                ))
                temporary_orphans.append(post)
            else:
                # TODO: What happens if I try to save a Post with the same
                # ID as another Post already in the database? Is there a
                # special way of asking Django to overwrite it, or will
                # this work on its own?
                #
                # Seems like .save() just overwrites the way you'd expect.
                sqlfied_post.save()
                made_progress = True

            # Check for gaps in the ID's, that indicate deleted posts.
            # TODO: But this won't catch posts in the seams between
            #       200-post batches. Ugh, what a thorny problem.
            if i > 0:
                post_id      = post['id']
                prev_post_id = posts[i-1]['id']

                for deleted_id in range(prev_post_id+1, post_id):
                    try:
                        to_delete = Post.objects.get(
                            id_num__exact=deleted_id)
                    except Post.DoesNotExist:
                        pass
                    else:
                        self.stdout.write(
                            f"Deleting {to_delete} because it no longer "
                            "exists on Hypnohub.")
                        to_delete.delete()

        temporary_orphans = sorted(
            temporary_orphans,
            key=lambda post: post['id'])

        return made_progress, temporary_orphans

    def handle(self, *args, **kwargs):
        self.stdout.write(
            "Updating local cache of Hypnohub "
            + self.style.SQL_TABLE("Post")
            + "s...")
        self.stdout.write("")

        self.stdout.write("Checking robots.txt...")
        har = HypnohubAPIRequester()

        self.stdout.write("Getting post data... (this is going to "
            "take 20+ minutes)")

        # There's a problem with just blindly going through all the posts in
        # numerical order. And that problem is:
        #
        # The Post model has a 'parent' field, and this field *has* to refer
        # to another Post, or be set to 'null'. But what if the parent has a
        # higher ID than the child? We won't be able to save it with the
        # 'parent' field set, because we don't have any record of the post it's
        # refering to, yet. Here's my solution:
        #
        # We'll go through every post on the site and try to turn them all into
        # Posts. As we're doing this, we'll set aside any posts with a 'parent'
        # that we haven't saved yet. We'll put them all in a list called
        # 'temporary_orphans'.
        #
        # Then, after we're done with every post that isn't a temporary_orphan,
        # we'll do the same process with the orphans themselves: Go through
        # each one and check if we can turn them into a savable Post. If not,
        # we'll save them for later... again.
        #
        # At this point there's a fork in the road. Either we've managed to
        # save at least one orphan, or we haven't.
        #
        # If we haven't, there's no point in trying again. We'd just loop
        # infinitely. So the best we can do is to print the ID's of the Posts
        # we're having trouble with, and save them with 'parent' set to 'null'.
        #
        # But if we *have* saved at least one, that means we need to try the
        # other orphans again. After all, the saved posts are almost definitely
        # the parents of some of the orphans on our list. And at this point we
        # just keep looping until we run out of orphans or we stop making
        # progress.
        #
        # By the way, it's probably best to go through posts in ascending
        # order, by ID. Because that way we'll process old posts first, then
        # new posts. And a child post is very likely to have been created
        # *after* its parent, and not before.

        made_progress = False
        posts = []

        for new_posts, highest_id_seen, highest_id in (
                    har.get_complete_post_list()):
            made_progress, posts = self.save_all_posts(new_posts)
            self.stdout.write(
                f"\r({highest_id_seen:5}/{highest_id}) "
                f"Latest batch size: {len(new_posts):3}", ending='')
            self.stdout.flush()

        self.stdout.write("\n")
        self.stdout.write(f"Un-orphaning {len(posts)} posts...")

        for cycle_num in itertools.count(1):
            if len(posts) == 0:
                break

            self.stdout.write(f"\rPass #{cycle_num}... ", ending='')
            self.stdout.flush()

            # TODO: This is an infinite loop for some reason.
            #       But good luck testing it because it takes 20 minutes
            #       each time it's run. Should probably give it a debug
            #       mode.
            #
            #       But I'm pretty sure I fixed the problem: It was running
            #       with posts = []
            made_progress, posts = self.save_all_posts(posts)

            if not made_progress:
                self.stdout.write(self.style.ERROR(
                    "Failed to get the parents for the following ID's:"))
                self.stdout.write("[child id] -> [parent id]")

                for post in posts:
                    self.stdout.write(f"{post['id']} -> {post['parent']}")
                    del post['parent']

                self.stdout.write(self.style.ERROR(
                    "So instead, we have to save them with parent=null."))

                self.save_all_posts(posts)
                break

        self.stdout.write("done.")
