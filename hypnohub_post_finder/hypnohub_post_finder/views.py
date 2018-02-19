from django.shortcuts import render

def best(request):
    context = {
        'post_id': 1337,
        'image_url': "http://hypnohub.net/data/image/2d3bec75d3c52b70f61e592250b22ed7.jpg"
    }

    return render(template_name='post_view.html',
                  request=request,
                  context=context)

hot = best
random = best

# Create your views here.
