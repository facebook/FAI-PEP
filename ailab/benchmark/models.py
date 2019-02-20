# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


class BenchmarkInfo(models.Model):
    command = models.TextField(null=False)
    start_time = models.DateTimeField(null=True)
    done_time = models.DateTimeField(null=True)
    status = models.CharField(max_length=10,
                              choices=[('Q', 'QUEUE'),
                                       ('C', 'CLAIMED'),
                                       ('R', 'RUNNING'),
                                       ('D', 'DONE'),
                                       ('F', 'FAILED'),
                                       ('E', 'USER_ERROR')],
                              default='QUEUE',
                              null=False)

    result = models.TextField(null=True)
    identifier = models.BigIntegerField(null=False)
    claimer = models.CharField(max_length=40, null=True)
    benchmarks = models.TextField(null=True)
    claimed_time = models.DateTimeField(null=True)
    device = models.CharField(max_length=40, null=True)
    log = models.TextField(null=True)
    failed_time = models.DateTimeField(null=True)
    user = models.CharField(max_length=40, null=True)
    job_queue = models.CharField(max_length=40,
                                 null=False,
                                 default='pep_interactive')
    queue_time = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['identifier']),
            models.Index(fields=['claimer']),
            models.Index(fields=['device']),
            models.Index(fields=['job_queue']),
        ]


class Device(models.Model):
    device = models.CharField(max_length=64, null=True)
    status = models.CharField(max_length=9,
                              choices=[('AVA', 'AVAILABLE'),
                                       ('OCC', 'OCCUPIED'),
                                       ('OFF', 'OFFLINE'),
                                       ('DIS', 'DISABLED')],
                              null=True)
    claimer = models.CharField(max_length=40, null=True)
    hash = models.CharField(max_length=32, null=True, unique=True)
    update_time = models.DateTimeField(null=True)
    heartbeat_time = models.DateTimeField(null=True)
    job_queue = models.CharField(max_length=40,
                                 null=False,
                                 default='pep_interactive')

    class Meta:
        indexes = [
            models.Index(fields=['device']),
            models.Index(fields=['status']),
            models.Index(fields=['claimer']),
            models.Index(fields=['job_queue']),
        ]
