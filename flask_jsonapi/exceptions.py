class JsonApiException(Exception):
    title = 'Unknown error'
    status = 500

    def __init__(self, source, detail, *args, title=None, status=None, **kwargs):
        """Initialize a jsonapi exception

        :param dict source: the source of the error
        :param str detail: the detail of the error
        """
        super().__init__(*args, **kwargs)
        self.source = source
        self.detail = detail
        if title is not None:
            self.title = title
        if status is not None:
            self.status = status

    def to_dict(self):
        return {'status': self.status,
                'source': self.source,
                'title': self.title,
                'detail': self.detail}


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

    def __init__(self, detail, source=None, **kwargs):
        source = source or {}
        super().__init__(
            source=source,
            detail=detail,
            **kwargs,
        )


class InvalidType(JsonApiException):
    title = "Invalid type"
    status = 409


class NotImplementedMethod(JsonApiException):
    title = "Method not implemented"
    status = 501

    def __init__(self, detail, **kwargs):
        super().__init__(
            source=None,
            detail=detail,
            **kwargs
        )


class ForbiddenError(JsonApiException):
    title = 'Operation forbidden.'
    status = 403

    def __init__(self, detail, source=None):
        self.source = source or {}
        self.detail = detail


class AttributeValidationError(JsonApiException):
    title = 'Attribute error'
    status = 422

    def __init__(self, detail, source=None, attribute=None):
        if source or attribute:
            self.source = source or {'pointer': 'data/attributes/{}'.format(attribute)}
        else:
            self.source = {}
        self.detail = detail
