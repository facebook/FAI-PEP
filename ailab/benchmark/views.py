# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig

import db_controller
import benchmark_result_controller
from result_filter import ResultFilter
from result_table import ResultTable
from .models import BenchmarkResult


PLOTABLE_COL_SET = {
    'num_runs',
    'control_commit_time', 'commit_time',
    'control_stdev', 'stdev',
    'control_mean', 'mean', 'diff_mean',
    'control_p0', 'p0', 'diff_p0',
    'control_p10', 'p10', 'diff_p10',
    'control_p50', 'p50', 'diff_p50',
    'control_p90', 'p90', 'diff_p90',
    'control_p100', 'p100', 'diff_p100',
    'control_p95', 'p95',
    'control_p99', 'p99',
}

COL_PER_ROW = 1


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


def visualize(request):
    # Get columns included from user-specified checkbox list
    include_column_list = request.GET.getlist('columns')
    include_column_set = set(include_column_list)

    # Filter data base on request
    f = ResultFilter(request.GET, queryset=BenchmarkResult.objects.all())
    qs = f.qs

    # Build table with specified columns
    table = ResultTable(qs)
    available_columns = []
    exclude_column_list = []
    for name, _ in table.base_columns.items():
        if name != 'time':
            available_columns.append(name)
            if name not in include_column_set:
                exclude_column_list.append(name)
    table.exclude = tuple(exclude_column_list)

    RequestConfig(request, paginate={'per_page': 25}).configure(table)

    # Build graph to display
    # TODO: Currently X axis is fixed to time
    labels = [o.time * 1000 for o in qs]
    chartdata = {'x': labels}

    # Construct data to display
    for i in range(len(include_column_list)):
        column = include_column_list[i]
        if column not in PLOTABLE_COL_SET:
            continue

        index = i + 1
        vals = [getattr(o, column) for o in qs]

        chartdata['name{}'.format(index)] = column
        chartdata['y{}'.format(index)] = vals

    # Chart info for NVD3
    charttype = "lineChart"
    chartcontainer = 'linechart_container'  # container name
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': True,
            'tag_script_js': True,
            'jquery_on_ready': False,
            'x_axis_format': '%b %d %H:%m',
        }
    }

    data['filter'] = f
    data['table'] = table
    data['available_columns'] = zip(*[iter(available_columns)] * COL_PER_ROW)
    return render(request, 'result_visualization.html', data)
