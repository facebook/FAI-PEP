from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

import django_tables2 as tables
from .models import BenchmarkResult


class ResultTable(tables.Table):
    def render_time(self, value):
        return datetime.utcfromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')

    class Meta:
        model = BenchmarkResult
        template_name = 'django_tables2/bootstrap.html'
