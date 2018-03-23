import flask

from flask_jsonapi import exceptions


class Pagination:
    def parse(self):
        raise NotImplementedError


class SizeNumberPagination(Pagination):
    def parse(self):
        size = flask.request.args.get('page[size]')
        number = flask.request.args.get('page[number]')
        if size is None and number is None:
            return {}
        elif size is None or number is None:
            raise exceptions.InvalidPage('One of page parameters wrongly or not specified.')
        else:
            try:
                size = int(size)
                number = int(number)
            except ValueError:
                raise exceptions.InvalidPage('Page parameters must be integers.')
            return {'size': size, 'number': number}
