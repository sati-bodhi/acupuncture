from django.urls import path
from . import views

urlpatterns=[
    path('', views.homepage, name='index'),
    path('query', views.query, name='query'),
    path('diagnose', views.diagnose, name='diagnose'),
]