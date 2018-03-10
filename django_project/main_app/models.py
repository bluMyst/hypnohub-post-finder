import re

from django.db import models
from django.urls import reverse

from django.core.exceptions import ValidationError
from django.core import validators

md5_validator = validators.RegexValidator(
    regex="^[0-9a-f]{32}$",
    flags=re.IGNORECASE,
    code="invalid md5")

rating_validator = validators.RegexValidator(
    regex="^[sqe]$",
    code="invalid rating")

image_url_validator = validators.RegexValidator(
    regex="""
        ^

        # Images aren't given over SSL yet, but they might change that in the
        # future.
        https?://

        hypnohub.net

        # If you don't put a second slash in the URL, Hypnohub will still know
        # what you mean. But it'll never give you an image URL without that
        # second slash, so there's probably a reason for it.
        //?

        data/

        # This part seems to always be 'preview', 'sample', or 'file'. But I'm
        # not going to be so strict with validation.
        [a-z0-9_-]+/

        # The md5 hash of the post.
        [0-9a-f]{32}

        # So far the only file extensions I've run across are .jpg, .gif, and
        # .png, but I'm trying to be very permissive in case Hypnohub changes
        # something.
        \.\w+

        $
    """,
    flags=re.IGNORECASE & re.VERBOSE,
    code="invalid image url")

# NOTE: Postgres (and probably most other SQL servers) doesn't compress its
# database file, so we might have to be careful about how efficiently we store
# data.

class Post(models.Model):
    def __str__(self):
        return f"#{self.id} by {self.author}"

    id = models.PositiveIntegerField(
        db_column='id',
        primary_key=True,
        help_text="A unique ID. Starts counting at one and is just incremented"
        " with every post.")

    tags = models.TextField(
        blank=True, # Though very unlikely, it *is* possible.
        help_text="Separated by single spaces. Can contain parenthesis,"
        " underscores, and probably other special characters.")

    score = models.PositiveIntegerField(
        help_text="The score given to this post by users voting on it and"
        " favoriting it. A 'good' is +1, 'great' is +2, and favoriting is +3."
        " Probably can't be negative.")

    rating = models.CharField(
        "content rating",
        max_length=1,
        validators=[rating_validator],

        choices=(
            ('s', 'safe'),
            ('q', 'questionable'),
            ('e', 'explicit')))

    author = models.CharField(max_length=32)

    # Even though Hypnohub gives URL's with no "http:", you need to add that on
    # before saving anything to the database.
    file_url = models.CharField(
        max_length=64,
        help_text='This is the "view larger version" image. Can have seemingly'
        ' any extension. For images with no "view larger version", this is the'
        ' main image.')

    sample_url = models.CharField(
        max_length=64,
        blank=True,
        help_text='This is what you see when you\'re on a page with a "view'
        ' larger version". file_url is the larger version. On pages with no'
        ' "view larger version", then you\'re shown the file_url instead.')

    preview_url = models.CharField(
        max_length=64,
        # Pretty sure this one can't be blank.
        help_text="This is what you see when you're looking at multiple images"
        " on the same page.")

    parent = models.OneToOneField(
        to='self',
        related_name='child',
        null=True,
        on_delete=models.SET_NULL)

    @property
    def page_url(self):
        return f"http://hypnohub.net/post/show/{self.id}"

    @property
    def permalink(self):
        # NOTE: This is temporary and needs to get changed in the far future if
        # this ever becomes a proper web service.
        return 'http://127.0.0.1:8000' + self.get_absolute_url()

    def get_absolute_url(self):
        return reverse('view-a-post-by-id', kwargs={'id': self.id})


class UserVote(models.Model):
    post = models.OneToOneField(
        to=Post,
        related_name='vote',
        primary_key=True,

        # If the Post is deleted, also delete this vote.
        on_delete=models.CASCADE,
    )

    vote_type = models.PositiveSmallIntegerField(
        choices=(
            ( 1, 'upvote'),
            ( 0, 'meh'),
            (-1, 'downvote'),
        ),
    )

    def __str__(self):
        return f"vote {self.vote_type:+} for #{self.post.id}"
