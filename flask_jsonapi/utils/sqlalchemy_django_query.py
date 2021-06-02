# -*- coding: utf-8 -*-
# flake8: noqa
"""
    sqlalchemy_django_query
    ~~~~~~~~~~~~~~~~~~~~~~~

    A module that implements a more Django like interface for SQLAlchemy
    query objects.  It's still API compatible with the regular one but
    extends it with Djangoisms.

    Example queries::

        Post.query.filter_by(pub_date__year=2008)
        Post.query.exclude_by(id=42)
        User.query.filter_by(name__istartswith='e')
        Post.query.filter_by(blog__name__exact='something')
        Post.query.order_by('-blog__name')

    :copyright: 2011 by Armin Ronacher, Mike Bayer.
    license: BSD, see LICENSE for more details.
"""
from sqlalchemy import exc
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.base import _entity_descriptor
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import extract
from sqlalchemy.sql import operators
from sqlalchemy.util import to_list
from sqlalchemy_utils.functions import orm

from flask_jsonapi import exceptions


def joinedload_all(column):
    elements = column.split('.')
    joined = joinedload(elements.pop(0))
    for element in elements:
        joined = joined.joinedload(element)
    return joined


class DjangoQueryMixin(object):
    """Can be mixed into any Query class of SQLAlchemy and extends it to
    implements more Django like behavior:

    -   `filter_by` supports implicit joining and subitem accessing with
        double underscores.
    -   `exclude_by` works like `filter_by` just that every expression is
        automatically negated.
    -   `order_by` supports ordering by field name with an optional `-`
        in front.
    """
    _underscore_operators = {
        'eq':           operators.eq,
        'ne':           operators.ne,
        'gt':           operators.gt,
        'lt':           operators.lt,
        'gte':          operators.ge,
        'lte':          operators.le,
        'contains':     operators.contains_op,
        'notcontains':  operators.notcontains_op,
        'exact':        operators.eq,
        'iexact':       operators.ilike_op,
        'startswith':   operators.startswith_op,
        'istartswith':  lambda c, x: c.ilike(x.replace('%', '%%') + '%'),
        'iendswith':    lambda c, x: c.ilike('%' + x.replace('%', '%%')),
        'endswith':     operators.endswith_op,
        'isnull':       lambda c, x: x and c != None or c == None,
        'range':        operators.between_op,
        'year':         lambda c, x: extract('year', c) == x,
        'month':        lambda c, x: extract('month', c) == x,
        'day':          lambda c, x: extract('day', c) == x
    }

    _underscore_list_operators = {
        'in': operators.in_op,
        'notin': operators.notin_op,
    }

    def filter_by(self, **kwargs):
        return self._filter_or_exclude(False, kwargs)

    def exclude_by(self, **kwargs):
        return self._filter_or_exclude(True, kwargs)

    def select_related(self, *columns, **options):
        depth = options.pop('depth', None)
        if options:
            raise TypeError('Unexpected argument %r' % iter(options).next())
        if depth not in (None, 1):
            raise TypeError('Depth can only be 1 or None currently')
        need_all = depth is None
        columns = list(columns)
        for idx, column in enumerate(columns):
            column = column.replace('__', '.')
            if '.' in column:
                need_all = True
            columns[idx] = column
        func = (need_all and joinedload_all or joinedload)
        return self.options(func(*columns))

    def order_by(self, *args):
        args = list(args)
        joins_needed = []
        for idx, arg in enumerate(args):
            q = self
            if not isinstance(arg, str):
                continue
            if arg[0] in '+-':
                desc = arg[0] == '-'
                arg = arg[1:]
            else:
                desc = False
            column = None
            for token in arg.split('__'):
                column = get_column(self._filter_by_zero(), token, joins_needed)
                if column and column.impl.uses_objects:
                    q = q.join(column)
                    joins_needed.append(column)
                    column = None
            if column is None:
                raise exceptions.InvalidSort(
                    "You can't sort on {}, {}".format(token, str(arg)))
            if desc:
                column = column.desc()
            args[idx] = column

        q = super(DjangoQueryMixin, self).order_by(*args)
        for join in joins_needed:
            q = q.join(join)
        return q

    def _filter_or_exclude(self, negate, kwargs):
        q = self
        negate_if = lambda expr: expr if not negate else ~expr
        column = None
        joins_needed = []
        for arg, value in kwargs.items():
            for token in arg.split('__'):
                if column is None:
                    column = get_column(self._filter_by_zero(), token, joins_needed)
                    if column and column.impl.uses_objects:
                        q = q.join(column)
                        joins_needed.append(column)
                        column = None
                elif token in self._underscore_operators:
                    op = self._underscore_operators[token]
                    q = q.filter(negate_if(op(column, *to_list(value))))
                    column = None
                elif token in self._underscore_list_operators:
                    op = self._underscore_list_operators[token]
                    q = q.filter(negate_if(op(column, to_list(value))))
                    column = None
                else:
                    raise ValueError('No idea what to do with %r' % token)
            if column is not None:
                q = q.filter(negate_if(column == value))
                column = None
            q = q.reset_joinpoint()
        return q


class DjangoQuery(DjangoQueryMixin, Query):
    pass


def get_column(joinpoint, token, joins_needed):
    try:
        result = _entity_descriptor(get_mapper(joinpoint), token)
        if type(result) != property:
            return result
    except exc.InvalidRequestError:
        pass
    for join in joins_needed:
        try:
            return _entity_descriptor(join, token)
        except exc.InvalidRequestError:
            pass


def get_mapper(mixed):
    """
    Return related SQLAlchemy Mapper for given SQLAlchemy object.

    :param mixed: SQLAlchemy Table / Alias / Mapper / declarative model object

    ::

        from sqlalchemy_utils import get_mapper


        get_mapper(User)

        get_mapper(User())

        get_mapper(User.__table__)

        get_mapper(User.__mapper__)

        get_mapper(sa.orm.aliased(User))

        get_mapper(sa.orm.aliased(User.__table__))


    Raises:
        ValueError: if multiple mappers were found for given argument

    .. versionadded: 0.26.1
    """
    if isinstance(mixed, orm._MapperEntity):
        mixed = mixed.expr
    elif isinstance(mixed, orm.sa.Column):
        mixed = mixed.table
    elif isinstance(mixed, orm._ColumnEntity):
        mixed = mixed.expr

    if isinstance(mixed, orm.sa.orm.Mapper):
        return mixed
    if isinstance(mixed, orm.sa.orm.util.AliasedClass):
        return orm.sa.inspect(mixed).mapper
    if isinstance(mixed, orm.sa.sql.selectable.Alias):
        mixed = mixed.element
    if isinstance(mixed, orm.AliasedInsp):
        return mixed.mapper
    if isinstance(mixed, orm.sa.orm.attributes.InstrumentedAttribute):
        mixed = mixed.class_
    if isinstance(mixed, orm.sa.Table):
        if hasattr(orm.mapperlib, '_all_registries'):
            all_mappers = set()
            for mapper_registry in orm.mapperlib._all_registries():
                all_mappers.update(mapper_registry.mappers)
        else:  # SQLAlchemy <1.4
            all_mappers = orm.mapperlib._mapper_registry
        mappers = [
            mapper for mapper in all_mappers
            if mixed in {mapper.local_table}
        ]
        if len(mappers) > 1:
            raise Exception('Still to many mappers %s' % str(mappers))
        if not mappers:
            raise ValueError(
                "Could not get mapper for table '%s'." % mixed.name
            )
        else:
            return mappers[0]
    if not orm.isclass(mixed):
        mixed = type(mixed)
    return orm.sa.inspect(mixed)
