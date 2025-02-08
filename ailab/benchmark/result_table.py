from datetime import datetime

import django_tables2 as tables
from dateutil import tz

from .models import BenchmarkResult


class ResultTable(tables.Table):
    def render_time(self, value):
        from_zone = tz.gettz("UTC")
        to_zone = tz.gettz("US/Pacific")

        utc = datetime.fromtimestamp(value)
        utc = utc.replace(tzinfo=from_zone)

        return (
            str(value)
            + " ("
            + utc.astimezone(to_zone).strftime("%Y-%m-%d %H:%M:%S")
            + ")"
        )

    class Meta:
        model = BenchmarkResult
        template_name = "django_tables2/bootstrap.html"
