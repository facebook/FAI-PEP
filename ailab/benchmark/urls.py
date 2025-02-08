from django.conf.urls import url

from . import views

urlpatterns = [
    url(r"^$", views.handle_request, name="index"),
    url(r"^store-result$", views.store_benchmark_result, name="store_benchmark_result"),
    url(r"^visualize$", views.visualize, name="visualize"),
]
