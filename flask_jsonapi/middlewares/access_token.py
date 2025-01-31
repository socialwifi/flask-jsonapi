from . import base


class CheckAccessToken(base.Middleware):
    def create(self, *args, **kwargs):
        self._check_access_token()
        return super().create(*args, **kwargs)

    def read(self, *args, **kwargs):
        self._check_access_token()
        return super().read(*args, **kwargs)

    def read_many(self, *args, **kwargs):
        self._check_access_token()
        return super().read_many(*args, **kwargs)

    def update(self, *args, **kwargs):
        self._check_access_token()
        return super().update(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self._check_access_token()
        return super().destroy(*args, **kwargs)

    def _check_access_token(self):
        raise NotImplementedError
