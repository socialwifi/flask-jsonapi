class DataServiceException(Exception):
    def __init__(self, detail):
        self.detail = detail


class ResourceNotFound(DataServiceException):
    pass


class InvalidSortParameter(DataServiceException):
    pass

