# pyre-unsafe
from __future__ import absolute_import, division, print_function, unicode_literals

import bridge.django_auth
from bridge.auth_base import getAuthHandles


class Auth:
    def __init__(self, benchmark_db, app_id, token, is_test):
        self.app_id = app_id
        self.token = token

        self.auth_handles = getAuthHandles()

        handle = benchmark_db
        self.obj = None
        if handle in self.auth_handles:
            self.obj = self.auth_handles[handle](self.app_id, self.token, is_test)

    def get_auth_params(self):
        params = {}
        if self.obj is not None:
            params = self.obj.get_auth_params()
        return params
