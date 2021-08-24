# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from benchmark.models import BenchmarkInfo, Device
from django.contrib import admin


admin.site.register(BenchmarkInfo)
admin.site.register(Device)
