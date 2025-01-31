class JsonApiException(Exception):
    title = 'Unknown error'
    status = 500

    def __init__(self, *, status=None, title=None, detail=None, source=None):
        """Initialize a jsonapi exception

        :param dict source: the source of the error
        :param str detail: the detail of the error
        """
        if status is not None:
            self.status = status
        if title is not None:
            self.title = title
        self.detail = detail
        self.source = source

    def to_dict(self):
        result = {
            'status': self.status,
            'title': self.title,
        }
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


class InvalidType(JsonApiException):
    title = "Invalid type"
    status = 409


class NotImplementedMethod(JsonApiException):
    title = "Method not implemented"
    status = 501


class ForbiddenError(JsonApiException):
    title = 'Operation forbidden.'
    status = 403


class AttributeValidationError(JsonApiException):
    title = 'Attribute error'
    status = 422

    def __init__(self, detail, source=None, attribute=None):
        if source or attribute:
            self.source = source or {'pointer': 'data/attributes/{}'.format(attribute)}
        else:
            self.source = {}
        self.detail = detail
