from __future__ import absolute_import, division, print_function, unicode_literals

auth_handles = {}


class AuthBase:
    def __init__(self, app_id, token, is_test):
        pass

    def get_auth_params(self):
        pass


def registerAuth(name, obj):
    global auth_handles
    auth_handles[name] = obj


def getAuthHandles():
    return auth_handles
