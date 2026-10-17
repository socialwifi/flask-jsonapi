class Middleware:
    def create(self, *, data, inner):
        return inner.create(data=data)

    def read(self, *, id, inner):
        return inner.read(id=id)

    def list(self, *, filters, sorting, pagination, inner):
        return inner.list(filters=filters, sorting=sorting, pagination=pagination)

    def update(self, *, resource, data, inner):
        return inner.update(resource=resource, data=data)

    def destroy(self, *, resource, inner):
        return inner.destroy(resource=resource)
