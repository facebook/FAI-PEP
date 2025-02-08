from django.shortcuts import redirect


def redirect_to_viz(request):
    response = redirect("/benchmark/visualize")
    return response
