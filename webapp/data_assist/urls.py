from django.urls import path
from . import views

urlpatterns=[
    path('', views.homepage, name='index'),
    path('query', views.query, name='query'),
    path('diagnose', views.diagnose, name='diagnose'),
    path('diagnose/eight_principles', views.eight_principles, name='eight_principles'),
    path('diagnose/channels', views.channels, name='channels'),
    path('diagnose/channels/horary', views.horary, name='horary'),
    path('diagnose/elements', views.elements, name='elements'),
    path('diagnose/elements/acute', views.elements, name='elem-acute'),
    path('diagnose/elements/chronic', views.mushu, name='elem-chronic'),
    path('diagnose/extraordinary', views.extraordinary, name='extraordinary'),
    path('diagnose/jingjin', views.jingjin, name='jingjin'),
    path('diagnose/jingbie', views.jingbie, name='jingbie'),
    path('diagnose/luo', views.luo, name='luo'),
    path('diagnose/group_luo', views.group_luo, name='group_luo'),
]