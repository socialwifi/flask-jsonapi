class DataService:
    def create(self, *, data):
        raise NotImplementedError('Creating is not implemented.')

    def get_detail(self, *, id):
        raise NotImplementedError('Getting object is not implemented.')

    def get_list(self, *, filters, sorting, pagination):
        raise NotImplementedError('Getting list is not implemented.')

    def update(self, *, id, data, resource=None):
        raise NotImplementedError('Updating is not implemented')

    def destroy(self, *, id):
        raise NotImplementedError('Deleting is not implemented')

    def get_count(self, *, filters):
        raise NotImplementedError('Counting is not implemented')
