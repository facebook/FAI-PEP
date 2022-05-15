from __future__ import absolute_import, division, print_function, unicode_literals

from bridge.auth_base import AuthBase, registerAuth


class DjangoAuth(AuthBase):
    def __init__(self, app_id, token, is_test):
        pass

    def get_auth_params(self):
        return {}


registerAuth("django", DjangoAuth)
