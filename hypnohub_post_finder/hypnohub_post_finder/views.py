from django.shortcuts import render

def view_id(request, id_):
    context = {
        'post_id': id_,

        # TODO: Retrieve preview url from hhapi.
        # TODO: Store Hypnohub data in the database.
        'image_url': "http://hypnohub.net/data/image/2d3bec75d3c52b70f61e592250b22ed7.jpg"
    }

    return render(template_name='post_view.html',
                  request=request,
                  context=context)

def best(request):
    view_id(request, 1337)

hot = best
random = best
