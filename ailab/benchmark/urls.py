from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.handle_request, name='index'),
]
