from flask_jsonapi import data_services


class _Link(data_services.DataService):
    def __init__(self, middleware, inner):
        self.middleware = middleware
        self.inner = inner

    def create(self, *, data):
        return self.middleware.create(data=data, inner=self.inner)

    def read(self, *, id):
        return self.middleware.read(id=id, inner=self.inner)

    def list(self, *, filters, sorting, pagination):
        return self.middleware.list(filters=filters, sorting=sorting, pagination=pagination, inner=self.inner)

    def update(self, *, resource, data):
        return self.middleware.update(resource=resource, data=data, inner=self.inner)

    def destroy(self, *, resource):
        return self.middleware.destroy(resource=resource, inner=self.inner)


def build_pipeline(middlewares, data_service):
    pipeline = data_service
    for middleware in reversed(middlewares):
        pipeline = _Link(middleware, pipeline)
    return pipeline
