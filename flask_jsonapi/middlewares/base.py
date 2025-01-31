import typing


class Middleware:
    def create(self, *, middlewares: typing.Iterator['Middleware'], data_service, data):
        return next(middlewares).create(middlewares=middlewares, data_service=data_service, data=data)

    def read(self, *, middlewares: typing.Iterator['Middleware'], data_service, id):
        return next(middlewares).read(middlewares=middlewares, data_service=data_service, id=id)

    def read_many(self, *, middlewares: typing.Iterator['Middleware'], data_service, filters, sorting, pagination):
        return next(middlewares).read_many(
            middlewares=middlewares, data_service=data_service, filters=filters, sorting=sorting, pagination=pagination)

    def update(self, *, middlewares: typing.Iterator['Middleware'], data_service, id, data, data_service_kwargs=None):
        return next(middlewares).update(
            middlewares=middlewares, data_service=data_service, id=id, data=data,
            data_service_kwargs=data_service_kwargs)

    def destroy(self, *, middlewares: typing.Iterator['Middleware'], data_service, id):
        return next(middlewares).destroy(middlewares=middlewares, data_service=data_service, id=id)
