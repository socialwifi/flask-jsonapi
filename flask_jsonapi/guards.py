class Guard:
    """A request-level yes/no check that runs before the request body is parsed.

    A guard never sees the body, the object or the data service. It raises a
    :class:`flask_jsonapi.exceptions.JsonApiException` to reject the request.
    """

    def check(self, action):
        raise NotImplementedError
