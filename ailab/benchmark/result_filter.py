from __future__ import absolute_import, division, print_function, unicode_literals

import django_filters
from .models import BenchmarkResult


class ResultFilter(django_filters.FilterSet):
    user_identifier = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = BenchmarkResult
        exclude = ()
