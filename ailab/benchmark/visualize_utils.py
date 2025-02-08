import operator
from functools import reduce

from django.db.models import Q


def construct_single_q(rule):
    operator = rule["operator"]
    neg = False
    if operator.startswith("not_"):
        neg = True
        operator = operator[4:]

    cond = {
        "equal": "exact",
        "begins_with": "istartswith",
        "contains": "icontains",
        "ends_with": "iendswith",
        "less": "lt",
        "less_or_equal": "lte",
        "greater": "gt",
        "greater_or_equal": "gte",
        "between": "range",
    }[operator]

    if cond != "range":
        cond_dict = {"{}__{}".format(rule["id"], cond): rule["value"]}
    else:
        cond_dict = {"{}__{}".format(rule["id"], cond): tuple(rule["value"])}

    q_obj = Q(**cond_dict)

    if neg:
        q_obj = ~q_obj

    return q_obj


def construct_q(filters):
    # Base case
    if "condition" not in filters:
        return construct_single_q(filters)

    q_list = [construct_q(rule) for rule in filters["rules"]]

    if filters["condition"] == "AND":
        q_obj = reduce(operator.and_, q_list)
    else:
        q_obj = reduce(operator.or_, q_list)

    return q_obj
