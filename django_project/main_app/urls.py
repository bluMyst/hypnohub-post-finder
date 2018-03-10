from django.urls import path

from . import views

urlpatterns = [
    path('best',   views.best, name='view-a-best-post'),
    path('hot',    views.hot, name='view-a-hot-post'),
    path('random', views.random, name='view-a-random-post'),
    path('post/<int:id>', views.permalink, name='view-a-post-by-id'),

    path('', views.main_menu, name='main-menu'),
]
