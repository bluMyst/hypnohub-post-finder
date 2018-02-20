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

    md5 = models.CharField(
        max_length=32,
        unique=True,
        validators=[md5_validator],
        help_text="md5 hash of the full-sized(?) image. Used in the URL's for"
        " the full-sized, preview, and sample images.",
    )

    status = models.CharField(
        # TODO: Figure out what the 'status' field means and give it a better
        # description, better validators, and maybe make it a choice field.
        max_length=32,

        # Being as permissive as possible because I have no idea what to
        # expect.
        #blank=True,

        help_text="I have no idea what this field does but it always seems to"
        " be either 'active' or 'deleted'.",
    )

    width  = models.PositiveIntegerField()
    height = models.PositiveIntegerField()

class UserVote(models.Model):
    # TODO: Should have a validator checking if the Post exists or not.
    # Or! We should structure the database so that non-existent Posts aren't
    # saved. I mean, they *are* kinda useless.
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
