from __future__ import absolute_import, division, print_function, unicode_literals
from benchmark.models import BenchmarkInfo, Device
from django.utils import timezone


def get_payload(req):
    action = req.get('action')
    identifier = req.get('identifier')
    benchmarks = req.get('benchmarks')
    ids_str = req.get('ids')
    id = req.get('id')
    claimer = req.get('claimer')
    result = req.get('result')
    devices_str = req.get('devices')
    user = req.get('user')
    job_queue = req.get('job_queue')

    assert action is not None, "action not provided"

    devices = []
    if devices_str is not None:
        devices = devices_str.split(',')
        if len(devices) == 1:
            if devices[0] == "":
                devices = []

    ids = []
    if ids_str is None and (action == 'run' or action == 'release'):
        assert False, "ids must be specified for " + action
    elif ids_str is not None:
        ids = ids_str.split(",")

    if action == "add":
        for device in devices:
            r = BenchmarkInfo(
                status="QUEUE",
                identifier=identifier,
                benchmarks=benchmarks,
                device=device,
                user=user,
                job_queue=job_queue
            )
            r.save()

            return {"status": "success"}

    elif action == "claim":
        for device in devices:
            queryset = BenchmarkInfo.objects.filter(status='CLAIMED',
                                                    device=device,
                                                    claimer=claimer,
                                                    job_queue=job_queue)
            if not queryset:
                queryset = BenchmarkInfo.objects.filter(status='QUEUE',
                                                        device=device,
                                                        job_queue=job_queue)
                if queryset:
                    r = queryset[0]
                    r.status = "CLAIMED"
                    r.claimed_time = timezone.now()
                    r.claimer = claimer
                    r.save()

        Device.objects.filter(device__in=devices)\
                      .update(heartbeat_time=timezone.now())

        queryset = BenchmarkInfo.objects.filter(status="CLAIMED",
                                                claimer=claimer)

        return {
            'status': "success",
            'values': list(queryset.values())
        }

    elif action == "run":
        BenchmarkInfo.objects.filter(id__in=ids,
                                     claimer=claimer,
                                     job_queue=job_queue)\
                             .update(status="RUNNING",
                                     start_time=timezone.now())
        return {'status': "success"}

    elif action == "release":
        BenchmarkInfo.objects.filter(id__in=ids, job_queue=job_queue)\
                             .update(status="QUEUE",
                                     claimed_time=None,
                                     start_time=None,
                                     claimer=None)
        return {'status': "success"}

    elif action == "done":
        assert id is not None, "id must be specified for " + action

        log = req.get('log')
        assert log is not None, "Log field is empty"

        status = req.get('status')
        assert status == "DONE" or \
            status == "FAILED" or \
            status == "USER_ERROR",\
            "Unknown status " + status

        BenchmarkInfo.objects.filter(id=id, job_queue=job_queue)\
                             .update(status=status,
                                     done_time=timezone.now(),
                                     result=result,
                                     log=log)

        return {'status': "success"}

    elif action == "status":
        queryset = BenchmarkInfo.objects.filter(identifier=identifier,
                                                job_queue=job_queue)

        return {
            'status': "success",
            'values': list(queryset.values('status', 'id', 'device'))
        }

    elif action == "get":
        queryset = BenchmarkInfo.objects.filter(id__in=ids,
                                                job_queue=job_queue)

        return {
            'status': "success",
            'values': list(queryset.values())
        }

    elif action == "list_devices":
        # Two options: (1) If job_queue=*, it will query all non DISABLED devices;
        # (2) Otherwise, it will query non DISABLED devices from the specified
        # job_queue.
        queryset = Device.objects.exclude(status="DISABLED")
        if job_queue != "*":
            queryset = Device.objects.filter(job_queue=job_queue)

        return {
            'status': "success",
            'values': list(queryset.values())
        }

    elif action == "update_devices":
        reset = req.get('reset')

        if reset == "true":
            Device.objects.filter(claimer=claimer)\
                          .update(status="DISABLED",
                                  update_time=timezone.now())

        for device in devices:
            d = device.split("|")
            assert len(d) == 3, "Must have three elements in the input"
            data = {
                'device': d[0],
                'hash': d[1],
                'status': "OCCUPIED" if d[2] == "0"
                          else "AVAILABLE" if d[2] == "1"
                          else "OFFLINE",
                'claimer': claimer,
                'job_queue': job_queue,
            }

            defaults = {
                'device': data['device'],
                'status': data['status'],
                'claimer': data['claimer'],
                'job_queue': data['job_queue'],
                'update_time': timezone.now(),
                'heartbeat_time': timezone.now(),
            }

            obj, created = Device.objects.update_or_create(
                hash=data['hash'],
                defaults=defaults,
            )

            obj.save()

        return {'status': "success"}

    else:
        assert False, "action " + action + " not recognized"
