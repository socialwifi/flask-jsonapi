import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class ListResult:
    items: list
    total: typing.Optional[int]


class DataService:
    def create(self, *, data):
        raise NotImplementedError('Creating is not implemented.')

    def read(self, *, id):
        raise NotImplementedError('Reading is not implemented.')

    def list(self, *, filters, sorting, pagination) -> ListResult:
        raise NotImplementedError('Listing is not implemented.')

    def update(self, *, resource, data):
        raise NotImplementedError('Updating is not implemented.')

    def destroy(self, *, resource):
        raise NotImplementedError('Destroying is not implemented.')
