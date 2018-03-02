from django.db import models

from django.core.exceptions import ValidationError
from django.core import validators

md5_validator = validators.RegexValidator(
    regex="^[0-9a-fA-F]{32}$",
    code="invalid_md5",
)

rating_validator = validators.RegexValidator(
    regex="^[sqe]$",
    code="invalid_rating",
)

# NOTE: Postgres (and probably most other SQL servers) doesn't compress its
# database file, so we might have to be careful about how efficiently we store
# data.

# TODO: More validation!

class Post(models.Model):
    id_num = models.PositiveIntegerField(
        db_column='id',
        primary_key=True,
        help_text="A unique ID. Starts counting at one and is just incremented"
        " with every post.",
    )

    tags = models.TextField(
        blank=True, # Though very unlikely, it *is* possible.
        help_text="Separated by single spaces. Can contain parenthesis,"
        " underscores, and probably other special characters.",
    )

    score = models.PositiveIntegerField(
        help_text="The score given to this post by users voting on it and"
        " favoriting it. A 'good' is +1, 'great' is +2, and favoriting is +3."
        " Probably can't be negative.",
    )

    rating = models.CharField(
        "content rating",
        max_length=1,
        validators=[rating_validator],

        choices=(
            ('s', 'safe'),
            ('q', 'questionable'),
            ('e', 'explicit'),
        ),

        help_text="HypnoHub returns it as 's', 'q', or 'e' so that's how we"
        " store it.",
    )

    author = models.CharField(
        max_length=32,
    )

    # TODO: Just store one image url, because we only need to show the user the
    # image at one size.

    # Even though Hypnohub gives URL's with no "http:", please add that on
    # before saving anything to the database.
    file_url = models.CharField(
        max_length=64,
        help_text='This is the "view larger version" image. Can have seemingly'
        ' any extension. For images with no "view larger version", this is the'
        ' main image.',
    )

    sample_url = models.CharField(
        max_length=64,
        blank=True,
        help_text='This is what you see when you\'re on a page with a "view'
        ' larger version". file_url is the larger version. On pages with no'
        ' "view larger version", then you\'re shown the file_url instead.',
    )

    preview_url = models.CharField(
        max_length=64,
        # Pretty sure this one can't be blank.
        help_text="This is what you see when you're looking at multiple images"
        " on the same page.",
    )

    parent = models.OneToOneField(
        to='self',
        related_name='child',
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return f"#{self.id_num} by {self.author}"


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
        return f"vote {self.vote_type:+} for #{self.post.id_num}"
