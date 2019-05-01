# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.template.loader import render_to_string
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig

from .db_controller import get_payload
from .benchmark_result_controller import store_result
from .result_table import ResultTable
from .models import BenchmarkResult

from .visualize_utils import construct_q


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
    results = get_payload(data)

    return JsonResponse(results)


@csrf_exempt
def store_benchmark_result(request):
    data = json.loads(request.body)
    results = store_result(data)

    return JsonResponse(results)


def visualize(request):
    # Get columns included from user-specified checkbox list
    columns_sel = [] if request.GET.get('selection_form') is None \
        else json.loads(request.GET.get('selection_form'))
    include_column_set = set()
    graph_type = ''
    rank_column = ''
    for column in columns_sel:
        if column['name'] == 'columns':
            include_column_set.add(column['value'])
        if column['name'] == 'graph-type-dropdown':
            graph_type = column['value']
        if column['name'] == 'rank-column-dropdown':
            rank_column = column['value']

    # Filter data base on request
    filters = {} if request.GET.get('filters') is None \
        else json.loads(request.GET.get('filters'))
    if len(filters) != 0 and filters['valid']:
        result_q = construct_q(filters)
        qs = BenchmarkResult.objects.filter(result_q)
    else:
        qs = BenchmarkResult.objects.all()
        filters = {
            'condition': 'AND',
            'rules': [{}],
        }

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

    data = {}

    # Build graph to display
    if graph_type == 'bar-graph':
        labels = [str(i) for i in range(10)]

        # Construct data to display
        sort_attr = request.GET.get('sort')
        if sort_attr is None:
            sort_attr = '-' + rank_column
        else:
            rank_column = sort_attr
            if rank_column.startswith('-'):
                rank_column = rank_column[1:]
        column = sort_attr[1:] if sort_attr.startswith('-') else sort_attr

        sorted_qs = qs.order_by(sort_attr)[:10]
        labels = [o.type for o in sorted_qs]
        chartdata = {'x': labels}
        vals = [getattr(o, column) for o in sorted_qs]

        chartdata['name1'] = column
        chartdata['y1'] = vals

        # Chart info for NVD3
        charttype = "discreteBarChart"
        chartcontainer = 'linechart_container'  # container name
        data = {
            'charttype': charttype,
            'chartdata': chartdata,
            'chartcontainer': chartcontainer,
            'extra': {
                'x_is_date': False,
                'tag_script_js': True,
                'jquery_on_ready': False,
            }
        }

    else:
        labels = [o.time * 1000 for o in qs]
        chartdata = {'x': labels}

        # Construct data to display
        for column, i in zip(include_column_set, range(len(include_column_set))):
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

    data['table'] = table
    data['available_columns'] = zip(*[iter(available_columns)] * COL_PER_ROW)

    # Pass selection states to display
    data['filter_rules'] = json.dumps(filters)
    data['graph_type'] = graph_type
    data['rank_column'] = rank_column
    data['selected_columns'] = include_column_set

    if request.is_ajax():
        rendered_graph = render_to_string('graph_view.html', data, request)
        rendered_table = render_to_string('table_view.html', data, request)
        response = {
            'graph': rendered_graph,
            'table': rendered_table,
        }
        return HttpResponse(json.dumps(response))
    rendered = render_to_string('result_visualization.html', data, request)
    return HttpResponse(rendered)
