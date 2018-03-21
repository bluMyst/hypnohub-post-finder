import json

from django.shortcuts import render
from django.http import Http404, HttpResponse

from .models import Post, UserVote, UPVOTE, MEHVOTE, DOWNVOTE

def main_menu(request):
    context = {
        'title': "Site Map",

        'links': [
            ('view-a-best-post',
                 'View the best posts we can find for you.'),

            ('view-a-hot-post',
                 'View a mix of good and bad posts, to help train the AI.'),

            ('view-a-random-post',
                 'View posts completely at random, to teach the AI about your'
                 ' preferences.'),
        ],
    }

    return render(template_name='main_app/path_index.html',
                  request=request,
                  context=context)

def view_id(request, id, **context):
    context['post'] = Post.objects.get(id=id)

    return render(template_name='main_app/post_view.html',
                  request=request,
                  context=context)

def permalink(request, id):
    try:
        post = Post.objects.get(id=id)
    except Post.DoesNotExist:
        raise Http404('Post ID not found: ' + str(id))

    context = {'tabtitle': str(Post.objects.get(id=id)) + ' (permalink)'}
    return view_id(request, id, **context)

def best(request):
    return view_id(request, 1337, tabtitle="Best Posts")

def hot(request):
    return view_id(request, 1337, tabtitle="Hot Posts")

def random(request):
    return view_id(request, 1337, tabtitle="Random Posts")

def vote(request):
    try:
        id = json.loads(request.GET['id'])
        vote_type = json.loads(request.GET['up'])
    except KeyError:
        return HttpResponse("false", content_type="application/json")

    vote_type = UPVOTE if vote_type else DOWNVOTE

    try:
        post = Post.objects.get(id=id)
    except Post.DoesNotExist:
        return HttpResponse("false", content_type="application/json")

    try:
        vote = UserVote.objects.get(post=post)
    except UserVote.DoesNotExist:
        vote = UserVote(post=post, vote_type=vote_type)
    else:
        vote.vote_type = vote_type

    vote.save()

    return HttpResponse("true", content_type="application/json")
