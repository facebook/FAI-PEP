# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


# Create your models here.
class ModelFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/%d")
    upload_time = models.DateTimeField(auto_now_add=True, null=True)
