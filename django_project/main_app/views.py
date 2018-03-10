from django.shortcuts import render
from django.http import Http404

from .models import Post

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
