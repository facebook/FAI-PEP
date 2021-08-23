from __future__ import absolute_import, division, print_function, unicode_literals

from django.shortcuts import redirect


def redirect_to_viz(request):
    response = redirect("/benchmark/visualize")
    return response
