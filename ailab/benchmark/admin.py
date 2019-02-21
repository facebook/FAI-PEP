# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from benchmark.models import BenchmarkInfo, Device


admin.site.register(BenchmarkInfo)
admin.site.register(Device)
