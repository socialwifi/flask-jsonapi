class JsonApiException(Exception):
    title = 'Unknown error'
    status = 500

    def __init__(self, *args, status=None, title=None, detail=None, source=None):
        """Initialize a jsonapi exception

        Positional arguments are ``source, detail`` and any further ones go to ``Exception``, as in 1.4.

        :param int status: the HTTP status, overrides the class default
        :param str title: the title of the error, overrides the class default
        :param str detail: the detail of the error
        :param dict source: the source of the error
        """
        if args:
            source = args[0]
        if len(args) >= 2:
            detail = args[1]
        super().__init__(*([detail] if detail else []), *args[2:])
        self.source = source
        self.detail = detail
        if title is not None:
            self.title = title
        if status is not None:
            self.status = status

    def __str__(self):
        # 1.4 subclasses may skip super().__init__() and never set detail.
        detail = getattr(self, 'detail', None)
        return str(detail) if detail else super().__str__()

    def to_dict(self):
        result = {'status': self.status, 'title': self.title}
        if self.detail:
            result['detail'] = self.detail
        if self.source:
            result['source'] = self.source
        return result


class BadRequest(JsonApiException):
    title = "Bad request"
    status = 400


class InvalidField(BadRequest):
    title = "Invalid fields querystring parameter."

    def __init__(self, detail, **kwargs):
        super().__init__(
            source={'parameter': 'fields'},
            detail=detail,
            **kwargs
        )


class InvalidInclude(BadRequest):
    title = "Invalid include querystring parameter."

    def __init__(self, detail, **kwargs):
        super().__init__(
            source={'parameter': 'include'},
            detail=detail,
            **kwargs
        )


class InvalidFilters(BadRequest):
    title = "Invalid filters querystring parameter."

    def __init__(self, detail, **kwargs):
        super().__init__(
            source={'parameter': 'filters'},
            detail=detail,
            **kwargs
        )


class InvalidSort(BadRequest):
    title = "Invalid sort querystring parameter."

    def __init__(self, detail, **kwargs):
        super().__init__(
            source={'parameter': 'sort'},
            detail=detail,
            **kwargs
        )


class InvalidPage(BadRequest):
    title = "Invalid page querystring parameter."

    def __init__(self, detail, **kwargs):
        super().__init__(
            source={'parameter': 'page'},
            detail=detail,
            **kwargs
        )


class ObjectNotFound(JsonApiException):
    title = "Object not found"
    status = 404


class RelatedObjectNotFound(ObjectNotFound):
    title = "Related object not found"


class RelationNotFound(JsonApiException):
    title = "Relation not found"


class MethodNotAllowed(JsonApiException):
    title = "Method not allowed"
    status = 405

    def __init__(self, detail=None, source=None, **kwargs):
        super().__init__(source=source, detail=detail, **kwargs)


class InvalidType(JsonApiException):
    title = "Invalid type"
    status = 409


class NotImplementedMethod(JsonApiException):
    title = "Method not implemented"
    status = 501

    def __init__(self, detail=None, source=None, **kwargs):
        super().__init__(source=source, detail=detail, **kwargs)


class Conflict(JsonApiException):
    title = 'Conflict'
    status = 409


class Unauthorized(JsonApiException):
    title = 'Unauthorized'
    status = 401


class UnprocessableEntity(JsonApiException):
    title = 'Unprocessable entity'
    status = 422


class ServiceUnavailable(JsonApiException):
    title = 'Service unavailable'
    status = 503


class ForbiddenError(JsonApiException):
    title = 'Operation forbidden.'
    status = 403

    def __init__(self, detail=None, source=None, **kwargs):
        super().__init__(source=source, detail=detail, **kwargs)


class AttributeValidationError(JsonApiException):
    title = 'Attribute error'
    status = 422

    def __init__(self, detail, source=None, attribute=None):
        if source or attribute:
            self.source = source or {'pointer': 'data/attributes/{}'.format(attribute)}
        else:
            self.source = {}
        self.detail = detail
