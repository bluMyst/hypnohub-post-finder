from django.shortcuts import render

from .models import Post

# TODO: Every time the user requests something that requires knowledge about
# Post's, check what was the last time we've updated the database with fresh
# Hypnohub data. If it's been more than - say - a week, update it in a separate
# thread and set a flag so there's never more than one thread working. Make it
# Ctrl-C safe!
# https://stackoverflow.com/questions/842557/how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py

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
    # TODO: Error page on invalid id.
    context['post'] = Post.objects.get(id=id)

    return render(template_name='main_app/post_view.html',
                  request=request,
                  context=context)

def permalink(request, id):
    context = {'tabtitle': str(Post.objects.get(id=id)) + ' (permalink)'}
    return view_id(request, id, **context)

def best(request):
    return view_id(request, 1337, tabtitle="Best Posts")

def hot(request):
    return view_id(request, 1337, tabtitle="Hot Posts")

def random(request):
    return view_id(request, 1337, tabtitle="Random Posts")
