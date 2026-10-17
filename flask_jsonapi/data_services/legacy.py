from . import base


class LegacyRepositoryAdapter(base.DataService):
    def __init__(self, repository):
        self.repository = repository

    def create(self, *, data):
        return self.repository.create(data)

    def read(self, *, id):
        return self.repository.get_detail(id)

    def list(self, *, filters, sorting, pagination):
        items = self.repository.get_list(filters, sorting, pagination)
        total = self.repository.get_count(filters) if pagination else None
        return base.ListResult(items, total)

    def update(self, *, resource, data):
        return self.repository.update({**data, 'id': resource.id})

    def destroy(self, *, resource):
        return self.repository.delete(resource.id)
