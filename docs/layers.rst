Layers
======

.. versionadded:: 1.5.0

A :doc:`ViewSet <view_sets>` declares a resource as a stack of small layers. Each layer has one job and knows
nothing about the layers around it:

.. code-block:: text

    [HTTP request]
         |
    [Accept and Content-Type header checks]                        (406, 415)
         |
    allowed actions    - is this action served at all?             (405)
         |
    guards             - may this request be served at all?        (401, 403, ...)
         |
    [body or query string parsing]
         |
    object permissions - check every call against the client's rights (403)
         |
    middlewares        - wrap every call to the data service
         |
    data service       - loads and stores the data
         |
    [storage]

This page describes every layer, the order they run in and the errors they produce.

.. _layers-request-flow:

Request flow
------------

The order of the steps is fixed. No attribute of the ViewSet can change it:

1. Header checks: ``406`` for an ``Accept`` header other than ``application/vnd.api+json``, ``415`` for a
   ``POST`` or ``PATCH`` with a wrong ``Content-Type``.
2. Allowed actions: ``405`` if the ViewSet does not declare the action.
3. Guards, in list order.
4. Parsing of the body, or of the filters, sorting and pagination of a list. ``include`` and ``fields`` are
   parsed when the response is dumped.
5. Object permissions, when ``object_permissions`` is set.
6. Middlewares, in list order.
7. The data service.

Steps 5 to 7 form the pipeline, which the view calls with the methods listed in :ref:`layers-actions`. Allowed
actions and guards run **before** the request body is parsed, so a request that is not allowed or not
authenticated is rejected without looking at its payload.

The calls of every HTTP method:

List view, ``GET``:

1. ``allowed_actions`` check (``405`` if ``Actions.list`` is not allowed).
2. Guards, in list order.
3. Query string parsing: filters, sorting, pagination.
4. ``pipeline.list(filters=..., sorting=..., pagination=...)``, once. It returns a ``ListResult``; the response
   holds its items, and the pagination links are built from its total, see :ref:`layers-list-results`.

List view, ``POST``: allowed actions, guards, body parsing, ``pipeline.create(data=...)``, ``201``.

Detail view:

* ``GET``: allowed actions, guards, ``resource = pipeline.read(id=id)``, dump.
* ``PATCH``: allowed actions, guards, check that the ``id`` in the body matches the URL (``409`` if it does not),
  body parsing, ``resource = pipeline.read(id=id)``, ``pipeline.update(resource=resource, data=data)``.
  The answer is ``200`` with the dumped result, or ``204`` if the data service returned ``None``.
* ``DELETE``: allowed actions, guards, ``resource = pipeline.read(id=id)``,
  ``pipeline.destroy(resource=resource)``, ``204``.

On detail actions the object is loaded exactly once per request and handed down as ``resource``. The load in
``PATCH`` and ``DELETE`` goes through the pipeline like any other call, so the object permissions check read
permission when the object is loaded and update or delete permission when it is handed down: you must be able to
see an object to change it.

.. _layers-actions:

Allowed actions
---------------

``allowed_actions`` is a set of :class:`flask_jsonapi.Actions` values. It defaults to the empty set, so a ViewSet
that does not declare it serves nothing.

Each action has one method name, used by data services, middlewares, object permissions and the pipeline alike:

.. list-table::
   :header-rows: 1

   * - Action
     - HTTP request
     - Method
   * - ``Actions.create``
     - ``POST /articles/``
     - ``create(*, data)``
   * - ``Actions.read``
     - ``GET /articles/1/``
     - ``read(*, id)``
   * - ``Actions.list``
     - ``GET /articles/``
     - ``list(*, filters, sorting, pagination)``, returning a ``ListResult``
   * - ``Actions.update``
     - ``PATCH /articles/1/``
     - ``update(*, resource, data)``
   * - ``Actions.destroy``
     - ``DELETE /articles/1/``
     - ``destroy(*, resource)``

Middleware and object permission methods take the same keyword arguments plus ``inner``. ``PATCH`` and
``DELETE`` call ``read`` first to load the object.
``Actions.read_many`` is an alias of ``Actions.list`` with the same value, so a set that names either serves lists.

An action that is not listed is answered with ``405`` and a JSON:API error document. Data services therefore
implement every action they support and never raise "not allowed" themselves.

Guards
------

A guard is a request-level yes or no check. It never sees the body, the object or the data service.

.. code-block:: python

    import flask

    from flask_jsonapi import exceptions
    from flask_jsonapi import guards


    class CheckApiToken(guards.Guard):
        def check(self, action):
            if not token_is_valid(flask.request.headers.get('Authorization')):
                raise exceptions.Unauthorized(detail='A valid token is required.')

``token_is_valid`` stands for whatever check your application uses. A guard receives the action that is being
performed and rejects the request by raising a :class:`flask_jsonapi.exceptions.JsonApiException`. Guards run
inside the view, so the rejection is rendered as a JSON:API error document with the exception's status.

``guards`` is a list, checked in order. Guards raise exceptions instead of calling ``flask.abort()``; an
``abort()`` that is left in a guard is still turned into a JSON:API error (see :ref:`layers-errors`), but the
exceptions in :mod:`flask_jsonapi.exceptions` give you control over the detail.

Object permissions
------------------

Object permissions check every call to the data service against the client's rights: which objects it may see,
create, change and delete. ``ViewSet.object_permissions`` holds one object permission layer, or ``None`` (the
default) for no layer. The view places it outermost in the pipeline, after guards and parsing and before every
middleware, so its position never depends on a list. Like a middleware, it receives ``inner``, the rest of the
pipeline, with every call. Middlewares therefore see the filters the permission layer passes on: they may add
filters, but must not remove or replace the ones it added.

:class:`flask_jsonapi.permissions.CheckObjectPermission` is built on the
:class:`flask_jsonapi.permissions.PermissionChecker` interface. It calls the checker for every action:

* ``create``: ``check_create_permission(data=data)``, passing on the data the checker returns.
* ``read``: loads through ``inner``, then ``check_read_permission(resource=...)``.
* ``list``: passes ``apply_permission_filter(filters)`` to ``inner.list``, then runs ``check_list_permission`` on
  the items, see :ref:`layers-permission-filter`.
* ``update``: ``check_update_permission(resource=..., data=...)``, passing on the data the checker returns.
* ``destroy``: ``check_destroy_permission(resource=...)``.

Subclass it, give it a checker and implement ``apply_permission_filter``, which must return a new dict:

.. code-block:: python

    from flask_jsonapi import permissions


    class AuthorChecker(permissions.PermissionChecker):
        def check_read_permission(self, *, resource):
            return self._check(resource)

        def check_destroy_permission(self, *, resource):
            return self._check(resource)

        def check_update_permission(self, *, resource, data):
            return self._check(resource), data

        def check_create_permission(self, *, data):
            return {**data, 'author_id': current_author_id()}

        @staticmethod
        def _check(resource):
            if resource.author_id != current_author_id():
                raise permissions.PermissionException
            return resource


    class OwnArticles(permissions.CheckObjectPermission):
        permission_checker = AuthorChecker()

        def apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}

Set it with ``object_permissions = OwnArticles()``. ``current_author_id()`` stands for the way your application
identifies the client. It reads the client from the request on every call, because one instance serves all
requests, see :ref:`view-sets-instances`. A ``PermissionException`` answers ``403``, and the default
``check_list_permission`` leaves out of a list the objects that ``check_read_permission`` rejects.

.. _layers-permission-filter:

Lists: the permission filter and the safety net
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The permission checker decides which objects a client may see. ``apply_permission_filter`` puts the same
decision into the query, so the data service returns only those objects and the total includes only them. Its
contract:

* It returns new filters that restrict the list to the objects the client may list. It never mutates ``filters``.
* It may raise ``PermissionException`` when the client's own filters ask for objects the client may not list. The
  request answers ``403`` and the data service is not called.

Here articles belong to projects, and a client lists the articles of the projects it is a member of:

.. code-block:: python

    class MemberProjects(permissions.CheckObjectPermission):
        permission_checker = MemberChecker()

        def apply_permission_filter(self, filters):
            project_ids = member_project_ids()
            if 'project_id' in filters:
                if filters['project_id'] not in project_ids:
                    raise permissions.PermissionException(detail='You may not list this project.')
                return dict(filters)
            return {**filters, 'project_id__in': project_ids}

``MemberChecker`` and ``member_project_ids()`` stand for your own checker and lookup. The lookup returns the ids
in the form the filter schema parses them, strings for a ``FilterField`` with the default type.
``GET /articles/?filter[project_id]=7`` answers ``403`` when the client is not a member of project 7. Without a
``project_id`` filter, the layer restricts the list to the client's projects, and the database combines that with
every other filter.

After the data service returns, ``check_list_permission`` runs on the items as a safety net. When the filter is
right, it drops nothing and the result passes on unchanged. When it drops an object, the filter and the check
disagree: a bug in the filter, or a request crafted to exploit one. The total then includes objects the client may
not see, so the layer returns the remaining items with ``total=None`` and logs a warning on the
``flask_jsonapi.permissions.object_permissions`` logger, without any object data. A paginated response is then
shorter than the page size, so it has neither a ``next`` nor a ``last`` link, see :ref:`layers-list-results`.

To write an object permission layer of your own, subclass :class:`flask_jsonapi.permissions.ObjectPermissions`. It
has the methods of :ref:`layers-actions`, each with ``inner``, but no pass-through defaults: every method is
abstract, so you have to state the behaviour for every action and a forgotten ``list`` cannot silently allow
everything. Its ``list`` returns a ``ListResult``, see :ref:`layers-list-results`.

Middlewares
-----------

Middlewares are optional business layers between the object permissions and the data service. They have the
methods of :ref:`layers-actions`, and each one receives ``inner``, the rest of the chain, which has the same
interface as a data service. A middleware that does not override a method passes the call through unchanged.

.. code-block:: python

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

Subclass :class:`flask_jsonapi.middlewares.Middleware` and override only what you need. This middleware shows only
published articles, in the list and in its pagination total:

.. code-block:: python

    from flask_jsonapi import data_services
    from flask_jsonapi import middlewares


    class OnlyPublished(middlewares.Middleware):
        def list(self, *, filters, inner, **kwargs):
            return inner.list(filters={**filters, 'published': True}, **kwargs)

Code before the call to ``inner`` runs on the way in, code after it runs on the way out:

.. code-block:: python

    class LogRetitles(middlewares.Middleware):
        def update(self, *, resource, data, inner):
            old_title = resource.title
            result = inner.update(resource=resource, data=data)
            logger.info('Article %s retitled from %r to %r.', resource.id, old_title, result.title)
            return result

The view wraps the object permissions around the first middleware and each middleware around the next one, with
the data service innermost. The result is itself a data service, so the view only ever calls
``pipeline.<method>(...)``. Middlewares do not need to know about the list of middlewares or about the data
service. Middleware and data service instances are shared by all requests, so keep per-request state out of them,
see :ref:`view-sets-instances`.

Rules for middlewares:

* **List order is execution order.** With ``middlewares = [A(), B()]``, the code of ``A`` before ``inner`` runs
  first, then the code of ``B``, then the data service. Code after ``inner`` runs in the opposite order.
* **A middleware may call** ``inner`` **more than once.** Every call goes through the rest of the chain again:

  .. code-block:: python

      class RetryWhenUnavailable(middlewares.Middleware):
          def read(self, *, id, inner):
              try:
                  return inner.read(id=id)
              except data_services.Unavailable:
                  return inner.read(id=id)

* **Exceptions propagate.** Code after ``inner`` runs only when ``inner`` returns. A middleware must not swallow
  exceptions it does not handle, as the example above handles only ``Unavailable``.
* **Do not mutate the input in place.** ``filters`` and ``data`` may be shared with other layers. Build a new
  dict, as the examples above do with ``{**filters, ...}``, and pass that down.
* **A list returns a** ``ListResult``. A middleware that changes the items on the way out builds a new one. It
  keeps the total when every object stays, and sets it to ``None`` when it removes objects, because the total would
  include them:

  .. code-block:: python

      class HideEmbargoed(middlewares.Middleware):
          def list(self, *, inner, **kwargs):
              result = inner.list(**kwargs)
              visible = [article for article in result.items if not is_embargoed(article)]
              if len(visible) == len(result.items):
                  return result
              return data_services.ListResult(visible, total=None)

  ``is_embargoed`` stands for a rule of your own. A page that loses objects this way is short and has no ``next``
  link. Leaving objects out with a filter on the way in keeps the total and full pages, as ``OnlyPublished`` above
  does, so remove objects on the way out only when no filter can express the rule.

Required list filters
~~~~~~~~~~~~~~~~~~~~~

:class:`flask_jsonapi.middlewares.CheckRequiredListFilters` rejects a list request that lacks the named filters
with ``400``. The filters must also be declared in the ViewSet's ``filter_schema``. The names are the keys of the
parsed filters, as the data service receives them: ``filter[author_id][in]`` is checked as ``author_id__in``, and a
filter field declared with ``attribute=`` is checked under that attribute path, not under its query string name.

.. code-block:: python

    from flask_jsonapi.middlewares import CheckRequiredListFilters


    class ArticleViewSet(flask_jsonapi.ViewSet):
        filter_schema = ArticleFilterSchema()
        middlewares = [CheckRequiredListFilters(['title'])]

.. _layers-data-services:

Data services
-------------

A data service is the innermost layer. It has one method per action, with keyword-only arguments:

.. code-block:: python

    class DataService:
        def create(self, *, data): ...
        def read(self, *, id): ...
        def list(self, *, filters, sorting, pagination) -> ListResult: ...
        def update(self, *, resource, data): ...
        def destroy(self, *, resource): ...

:class:`flask_jsonapi.data_services.DataService` is the base class; a method you do not override raises
``NotImplementedError``, which is harmless as long as the action is not in ``allowed_actions``.

``resource`` is the object that ``read`` returned for this request. It is never ``None`` (a ``read``
that returns ``None`` answers ``404``) and a data service never has to load it again.

.. _layers-list-results:

List results
~~~~~~~~~~~~

``list`` returns a :class:`flask_jsonapi.data_services.ListResult` with two fields:

* ``items``: the objects of the requested page, or all matching objects when the request asks for no page.
* ``total``: the number of objects that match the filters, before pagination, or ``None``.

A data service sets ``total`` when ``pagination`` is given, and may leave it ``None`` otherwise. ``pagination`` is
a dict with ``size`` and ``number`` (starting at 1), or an empty dict when the request asks for no page. The
items and the total come from one call, so every filter a layer adds applies to both. :ref:`guide-list-source`
shows a data service that builds a ``ListResult`` itself.

The list view builds the pagination links from the result. With a total, the links are ``self``, ``first``,
``previous``, ``next`` and ``last``, and ``next`` is present up to the last page. With ``total=None`` the view
cannot know the last page: ``last`` is ``null``, and ``next`` is present only when the page is full, that is when
it holds ``size`` items. A short page has no ``next`` link. A full last page still has one, and the next page is
empty.

A data service is either a repository or a use case. A repository stores objects. A use case does something else
on the same endpoint, such as publishing an article or computing statistics:

.. code-block:: python

    class PublishArticles(data_services.DataService):
        def __init__(self, repository):
            self.repository = repository

        def read(self, *, id):
            return self.repository.read(id=id)

        def update(self, *, resource, data):
            return self.repository.update(resource=resource, data={'published': True})

SQLAlchemy repository
~~~~~~~~~~~~~~~~~~~~~

``flask_jsonapi.data_services.sqlalchemy_repositories.SqlAlchemyModelRepository`` stores a model in a SQLAlchemy
session. Set ``model`` and ``session``, and override ``filter_methods_map``, ``get_query``, ``build`` or
``update_attribute`` to customise it.

.. code-block:: python

    from flask_jsonapi.data_services import sqlalchemy_repositories


    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = session

* ``list`` filters the query from ``get_query`` once. When the request asks for a page, it counts that query for
  the total and returns the requested slice of the same query.
* ``update(resource=..., data=...)`` changes the object it is given and never fetches it again.
* ``destroy(resource=...)`` deletes the object it is given.
* Writes take a ``strategy``: ``'commit'`` (the default) or ``'flush'``.

Exceptions
~~~~~~~~~~

Data services are HTTP-agnostic. They raise the exceptions from :mod:`flask_jsonapi.data_services` and never HTTP
ones. Subclass a base class for your own business rules and the status follows:

.. code-block:: python

    class TitleLocked(data_services.InvalidData):
        pass


    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = session

        def update(self, *, resource, data, **kwargs):
            if resource.published and 'title' in data:
                raise TitleLocked('A published article cannot be retitled.', field='title')
            return super().update(resource=resource, data=data, **kwargs)

The SQLAlchemy repository translates database errors itself. An ``IntegrityError`` becomes ``Conflict``, an
``OperationalError`` (lost connection, timeout, deadlock) becomes ``Unavailable`` and any other ``SQLAlchemyError``
becomes a plain ``DataServiceException``. A ``DataError``, which the database raises for a malformed value such as
``not-a-uuid`` in a ``uuid`` column, is a client mistake and is translated by where it happened: ``read``
raises ``ResourceNotFound`` (no resource can have that id), ``list`` raises
``InvalidFilterParameter``, and the writing methods raise ``InvalidData``. The session is rolled back first, after
failed reads as well as writes, so an aborted transaction never reaches the next statement.

.. _layers-errors:

Errors
------

Every error a client receives from a flask-jsonapi view is a JSON:API error document. The view translates the
exceptions of the layers below it in one place, by base class, for every action:

.. list-table::
   :header-rows: 1

   * - Raised
     - HTTP status
   * - ``data_services.ResourceNotFound``
     - 404
   * - ``data_services.PermissionDenied``
     - 403
   * - ``data_services.InvalidData``
     - 422, with ``source.pointer`` set to ``/data/attributes/<field>`` when ``field`` is given
   * - ``data_services.Conflict``
     - 409
   * - ``data_services.InvalidSortParameter``, ``data_services.InvalidFilterParameter``
     - 400
   * - ``data_services.Unavailable``
     - 503
   * - any other ``data_services.DataServiceException``
     - 500, logged, with no internal details in the body
   * - a ``flask_jsonapi.exceptions.JsonApiException`` (from a guard, the object permissions, a middleware or the view)
     - its own ``status``
   * - a ``werkzeug.exceptions.HTTPException``, for example from ``flask.abort()``
     - the same status and title, keeping its headers such as ``WWW-Authenticate`` or ``Allow``
   * - an ``abort()`` carrying an explicit response, such as ``flask.abort(flask.Response(...))``
     - that response, returned unchanged: it is not a JSON:API document
   * - any other exception
     - 500, logged with ``logger.exception``, with no internal details in the body

A 500 stays a 500: the status is honest, what is hidden is the body.

:mod:`flask_jsonapi.exceptions` has the exceptions that guards and middlewares raise, among them ``Unauthorized``
(401), ``ForbiddenError`` (403), ``Conflict`` (409), ``UnprocessableEntity`` (422) and ``ServiceUnavailable``
(503). They take keyword arguments:

.. code-block:: python

    raise exceptions.ForbiddenError(detail='Only the author can do this.')
    raise exceptions.JsonApiException(status=418, title='Teapot', detail='Short and stout.', source={})

The older positional forms, such as ``JsonApiException(source, detail)``, keep working. Empty ``detail`` and
``source`` members are left out of the error object.

``view_decorators`` run outside the view, so the errors of a decorator are not converted to JSON:API documents.
Keep authentication in guards.

Rendering and presentation
--------------------------

Presentation belongs in the schema, not in the pipeline. A schema dumps once per object in the response and
never during permission loads, so a rendered field costs nothing on ``DELETE`` and nothing extra on ``PATCH``,
which dumps the returned object once.

Use a ``fields.Method`` to compute a read-only attribute on dump, and ``post_load`` to prepare incoming data
for saving:

.. code-block:: python

    import html

    import marshmallow

    from marshmallow_jsonapi import Schema
    from marshmallow_jsonapi import fields


    class ArticleSchema(Schema):
        id = fields.Int()
        title = fields.Str(required=True)
        body = fields.Str()
        body_html = fields.Method('render_body_html', dump_only=True)

        class Meta:
            type_ = 'articles'

        def render_body_html(self, article):
            return '<p>{}</p>'.format(html.escape(article.body or ''))

        @marshmallow.post_load
        def prepare_for_save(self, data, **kwargs):
            if 'title' in data:
                data['title'] = data['title'].strip()
            return data

``post_load`` also runs for ``PATCH``, where the schema is loaded with ``partial=True``, so it must cope with
missing attributes.

``view_decorators``
-------------------

``ViewSet.view_decorators`` wraps the view functions that Flask routes to. Use it only for Flask-level
integration that must wrap the view function itself, for example exempting the views from a CSRF extension:

.. code-block:: python

    class ArticleViewSet(flask_jsonapi.ViewSet):
        view_decorators = [csrf.exempt]

Do not use it for authentication or permissions. Use guards and object permissions, which run inside the view and
produce JSON:API errors.
