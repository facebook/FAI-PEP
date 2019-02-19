# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

from django.http import HttpResponse
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
import db_controller

@csrf_exempt
def handle_request(request):
    data = request.POST.copy()
    results = db_controller.get_payload(data)

    return JsonResponse(results)
