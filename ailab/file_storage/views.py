# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .models import ModelFile

from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def upload(request):

    # Handle file upload
    if request.method == 'POST' and 'file' in request.FILES:
        file = request.FILES['file']
        model_file = ModelFile(name=str(file), file=file)
        model_file.save()

        # Redirect to the document list after POST
        res = {
            "status": "success",
            "path": model_file.file.url,
        }
    else:
        res = {"status": "fail"}

    return JsonResponse(res)
