import typing

from flask_jsonapi import data_services

from . import base


class DataServiceAdapter(base.Middleware):
    def create(self, *, middlewares: typing.Iterator['Middleware'], data_service: data_services.DataService, data):
        return data_service.create(data=data)

    def read(self, *, middlewares: typing.Iterator['Middleware'], data_service: data_services.DataService, id):
        return data_service.get_detail(id=id)

    def read_many(self, *, middlewares: typing.Iterator['Middleware'], data_service: data_services.DataService,
                  filters, sorting, pagination):
        return data_service.get_list(filters=filters, sorting=sorting, pagination=pagination)

    def update(self, *, middlewares: typing.Iterator['Middleware'], data_service: data_services.DataService, id, data,
               data_service_kwargs=None):
        data_service_kwargs = data_service_kwargs or {}
        resource = data_service_kwargs.get('resource')
        return data_service.update(id=id, data=data, resource=resource)

    def destroy(self, *, middlewares: typing.Iterator['Middleware'], data_service: data_services.DataService, id):
        return data_service.destroy(id=id)
