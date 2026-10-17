class DataServiceException(Exception):
    def __init__(self, detail=None):
        super().__init__(detail)
        self.detail = detail


class ResourceNotFound(DataServiceException):
    pass


class PermissionDenied(DataServiceException):
    pass


class InvalidData(DataServiceException):
    def __init__(self, detail=None, field=None):
        super().__init__(detail)
        self.field = field


class Conflict(DataServiceException):
    pass


class InvalidSortParameter(DataServiceException):
    pass


class InvalidFilterParameter(DataServiceException):
    pass


class Unavailable(DataServiceException):
    pass
