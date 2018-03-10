import queue
import itertools
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main_app.hhapi import HypnohubAPIRequester
from main_app.models import Post

# Before you get too deep into this file, let me explain something:
#
# There's a problem with just blindly going through all the posts in
# numerical order, and saving them one by one. That problem is:
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

class Command(BaseCommand):
    help = "Updates the local database of Post's to match Hypnohub."

    def handle(self, *args, **kwargs):
        self.stdout.write("Updating local cache of Hypnohub Posts...\n\n")
        self.stdout.write("Checking robots.txt...")
        har = HypnohubAPIRequester()

        # At the time of this comment:
        #
        # There are about 60,000 posts on HypnoHub. hhapi is configured to wait
        # 2 seconds between each request, and each request is configured to
        # contain 200 posts. That means it'll take at least 10 minutes to go
        # through everything. But probably longer, because that doesn't include
        # the time it takes to munch on each batch of 200 posts.
        self.stdout.write(
            "Getting post data: (this will take about 10 minutes)")

        made_progress = False
        posts = []

        def printer_callback(highest_id_seen, highest_id):
            # Unfortunately, if you do the \r, ending='' trick to update the
            # same line, it'll mess up anything that save_all_posts tries to
            # print.
            timestamp = time.strftime("%H:%M:%S")
            self.stdout.write(
                f"{timestamp} Downloading... {highest_id_seen:5}/{highest_id}")

        _, temporary_orphans = self.save_all_posts(
            har.print_while_fetching(printer=printer_callback))
        self.stdout.write("")

        self.de_orphanizer(temporary_orphans)

        self.stdout.write("Finished updating! The database's Post cache should"
                          " now be synched with Hypnohub.")

    @transaction.atomic
    def save_all_posts(self, posts, delete_blank_spaces=True):
        """
        Takes a bunch of parsed-JSON posts and tries to save them to the
        database as Posts.

        delete_blank_spaces: If True, looks for gaps in the ID's, indicating
            deleted posts. Then makes sure we don't have any Post's in the
            database with those deleted ID's.

        Returns a tuple: (made_progress, temporary_orphans)

        temporary_orphans: A list of temporary orphans, sorted by id.

        made_progress: Whether any of the supplied posts were successfully
                       saved.

        Every post not returned as an orphan has been saved.
        """
        temporary_orphans = []
        made_progress = False

        blank_space_deleter = BlankSpaceDeleter(
            lambda post: self.stdout.write( self.style.NOTICE(
                f'Deleting cached Post "{post}" to match Hypnohub.')))

        for post in posts:
            if delete_blank_spaces:
                blank_space_deleter(post['id'])

            if post['parent'] != None and not self.id_is_cached(post['parent']):
                self.stdout.write( self.style.NOTICE(
                    f"Setting aside a temporarily orphaned post: "
                    f"{post['id']} with parent {post['parent']}"))
                temporary_orphans.append(post)
                continue

            if post['status'] in ['flagged', 'deleted']:
                if self.id_is_cached(post['id']):
                    to_delete = Post.objects.get(id=post['id'])
                    self.stdout.write( self.style.NOTICE(
                        f"Deleting Post {to_delete}, because Hypnohub reports"
                        f" that status={post['status']}"))
                    to_delete.delete()

                continue
            else:
                assert post['status'] == 'active', post['status']

            # NOTE: This assumes that all Post field names are identical to the
            # corresponding JSON field names (after processing by hhapi, of
            # course).

            # By the way, a concrete field is one that has a database column
            # associated with it. This filters out stuff like 'vote' and
            # 'child'.
            fields = {i.name: post[i.name]
                      for i in Post._meta.concrete_fields}

            Post.objects.update_or_create(id=post['id'], defaults=fields)
            made_progress = True

        temporary_orphans.sort(key=lambda post: post['id'])

        return made_progress, temporary_orphans

    def de_orphanizer(self, orphans):
        if len(orphans) > 0:
            self.stdout.write(
                f"Attempting to integrate {len(orphans)} orphans:")

        for cycle_num in itertools.count(1):
            if len(orphans) == 0:
                break

            self.stdout.write(f"\rPass #{cycle_num}... ", ending='')
            self.stdout.flush()

            made_progress, orphans = self.save_all_posts(orphans, False)

            if not made_progress:
                self.stdout.write( self.style.ERROR("ERROR"))
                self.stdout.write( self.style.ERROR(
                    "Failed to get the parents for the following ID's:"))
                self.stdout.write("child -> parent")

                for orphan in orphans:
                    self.stdout.write(f"{post['id']} -> {post['parent']}")
                    post['parent'] = None

                self.stdout.write( self.style.ERROR(
                    "So instead, we have to save them with parent=null."))

                self.save_all_posts(orphans)
                break
        else:
            self.stdout.write("done.")

    def id_is_cached(self, id):
        """
        Tells you if we have a Post with id=id already in the cache.
        """
        try:
            Post.objects.get(id=id)
        except Post.DoesNotExist:
            return False
        else:
            return True

class BlankSpaceDeleter:
    def __init__(self, printer):
        """
        printer will get called with Posts, just before they're deleted.
        """
        self.printer = printer

        # HypnoHub's id's start at 1.
        self.last_seen_id = 0

    def __call__(self, id):
        posts_to_delete = Post.objects.filter(
            id__gt=self.last_seen_id,
            id__lt=id)

        for post in posts_to_delete:
            self.printer(post)
            post.delete()

        self.last_seen_id = id
