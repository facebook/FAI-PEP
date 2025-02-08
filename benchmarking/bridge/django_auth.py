# pyre-unsafe

from bridge.auth_base import AuthBase, registerAuth


class DjangoAuth(AuthBase):
    def __init__(self, app_id, token, is_test):
        pass

    def get_auth_params(self):
        return {}


registerAuth("django", DjangoAuth)
