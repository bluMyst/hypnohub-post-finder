from django.contrib import admin
from .models import Post, UserVote

# Register your models here.
admin.site.register(Post)
admin.site.register(UserVote)
