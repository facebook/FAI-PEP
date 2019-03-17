# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
import db_controller
import benchmark_result_controller


@csrf_exempt
def handle_request(request):
    data = request.POST.copy()
    results = db_controller.get_payload(data)

    return JsonResponse(results)


@csrf_exempt
def store_benchmark_result(request):
    data = json.loads(request.body)
    results = benchmark_result_controller.store_result(data)

    return JsonResponse(results)
