Migrating to ViewSet
====================

.. versionadded:: 1.5.0

``ResourceRepositoryViewSet``, ``ProtectedViewSet``, their views and mixins, the ``AllowedActions`` mixins and
``resource_repositories`` are deprecated since 1.5.0. They are documented as deprecated but emit no warnings and
keep their behaviour, so you can upgrade flask-jsonapi first and move one endpoint at a time.

The only deliberate change for code that is not migrated is error handling, see :ref:`migration-errors`.

The example
-----------

Take an ``Article`` endpoint that is read and updated but never created or deleted, requires an API token, and
lets an author see only their own articles. This is how it looks with the legacy classes:

.. code-block:: python

    import functools

    import flask

    from flask_jsonapi import exceptions
    from flask_jsonapi import permissions
    from flask_jsonapi.resource_repositories import sqlalchemy_repositories


    def require_token(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if not token_is_valid(flask.request.headers.get('Authorization')):
                flask.abort(401)
            return view(*args, **kwargs)
        return wrapper


    class AuthorChecker(permissions.PermissionChecker):
        def check_read_permission(self, *, resource):
            return self._check(resource)

        def check_destroy_permission(self, *, resource):
            return self._check(resource)

        def check_update_permission(self, *, resource, data):
            return self._check(resource), data

        def check_create_permission(self, *, data):
            return data

        @staticmethod
        def _check(resource):
            if resource.author_id != current_author_id():
                raise permissions.PermissionException
            return resource


    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        instance_name = 'article'
        session = session

        def create(self, data, **kwargs):
            raise exceptions.ForbiddenError(detail='Articles cannot be created.')

        def delete(self, id, **kwargs):
            raise exceptions.ForbiddenError(detail='Articles cannot be deleted.')


    class ArticleListView(permissions.ProtectedListView):
        def _apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}


    class ArticleViewSet(permissions.ProtectedViewSet):
        schema = ArticleSchema
        repository = ArticleRepository()
        permission_checker = AuthorChecker()
        list_view_cls = ArticleListView
        view_decorators = [require_token]

Here is the same endpoint with ``flask_jsonapi.ViewSet``. The steps below explain each change.

.. code-block:: python

    import flask

    import flask_jsonapi

    from flask_jsonapi import exceptions
    from flask_jsonapi import guards
    from flask_jsonapi import permissions
    from flask_jsonapi.data_services import sqlalchemy_repositories


    class CheckApiToken(guards.Guard):
        def check(self, action):
            if not token_is_valid(flask.request.headers.get('Authorization')):
                raise exceptions.Unauthorized(detail='A valid token is required.')


    class AuthorChecker(permissions.PermissionChecker):
        ...  # unchanged


    class OwnArticles(permissions.CheckObjectPermission):
        permission_checker = AuthorChecker()

        def apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}


    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = session


    class ArticleViewSet(flask_jsonapi.ViewSet):
        schema_class = ArticleSchema
        allowed_actions = {
            flask_jsonapi.Actions.read,
            flask_jsonapi.Actions.list,
            flask_jsonapi.Actions.update,
        }
        guards = [CheckApiToken()]
        object_permissions = OwnArticles()
        data_service = ArticleRepository()

Step 1: authentication moves from ``view_decorators`` to ``guards``
-------------------------------------------------------------------

A decorator wraps the view function, so it runs outside the view. Whatever it raises or aborts with is not
handled by flask-jsonapi, and in the example the client gets an HTML error page. A guard runs inside the view,
before the body is parsed, and raises a JSON:API exception:

.. code-block:: python

    # before
    view_decorators = [require_token]

    # after
    guards = [CheckApiToken()]

``Unauthorized`` is the new 401 exception in :mod:`flask_jsonapi.exceptions`; raise exceptions instead of calling
``flask.abort()``. Keep ``view_decorators`` only for Flask-level integration, for example exempting the views
from a CSRF extension.

Step 2: "forbidden" stubs become ``allowed_actions``
----------------------------------------------------

The repository no longer says what it cannot do. The ViewSet says what it serves, and a request for anything else
is answered with 405 before the body is parsed:

.. code-block:: python

    # before: in the repository
    def create(self, data, **kwargs):
        raise exceptions.ForbiddenError(detail='Articles cannot be created.')

    def delete(self, id, **kwargs):
        raise exceptions.ForbiddenError(detail='Articles cannot be deleted.')

    # after: in the ViewSet
    allowed_actions = {
        flask_jsonapi.Actions.read,
        flask_jsonapi.Actions.list,
        flask_jsonapi.Actions.update,
    }

Note the status: a stub answered 403 Forbidden, a missing action answers 405 Method Not Allowed.

``Actions.list`` is the new name of ``Actions.read_many``. The old name stays as an alias with the same value, so
an ``allowed_actions`` that names ``Actions.read_many`` keeps serving lists, in legacy views and in a ViewSet.

Step 3: the permission checker moves into ``object_permissions``
----------------------------------------------------------------

``PermissionChecker`` classes keep working unchanged. What changes is where they are plugged in. Instead of
``ProtectedViewSet`` with a custom ``ProtectedListView``, a ``flask_jsonapi.permissions.CheckObjectPermission``
subclass holds the checker and goes into the ViewSet's ``object_permissions`` slot. Its ``apply_permission_filter``
replaces ``_apply_permission_filter`` of the list view:

.. code-block:: python

    # before
    class ArticleListView(permissions.ProtectedListView):
        def _apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}

    class ArticleViewSet(permissions.ProtectedViewSet):
        permission_checker = AuthorChecker()
        list_view_cls = ArticleListView

    # after
    class OwnArticles(permissions.CheckObjectPermission):
        permission_checker = AuthorChecker()

        def apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}

    class ArticleViewSet(flask_jsonapi.ViewSet):
        object_permissions = OwnArticles()

The list and its total now come from one call to the data service, with the permission filter applied, so the
total includes only objects the filter lets through. ``ProtectedListView`` applied ``_apply_permission_filter`` to
the list only, and took the total from ``get_count`` with the client's filters.

``apply_permission_filter`` has a contract: it returns filters that restrict the list to the objects the client may
list, and it may raise ``PermissionException`` (``403``) when the client's own filters ask for objects the client
may not list. ``check_list_permission`` still runs on the listed objects. When it drops any, ``ProtectedListView``
logged a warning and kept the total. ``CheckObjectPermission`` logs a warning without object data and leaves the
total out: the response has no ``last`` link, and a ``next`` link only for a full page. See
:ref:`layers-permission-filter`.

This changes what is checked on update and delete. The legacy ``ProtectedDetailView`` loaded the object for
``update`` and ``destroy`` without calling ``check_read_permission``, and whether a ``read()`` override of yours ran
on that load depended on where it sat in the class hierarchy. The new views load the object with ``read``
through the pipeline, once, and hand it to ``update`` or ``destroy`` as ``resource``. ``CheckObjectPermission``
therefore checks read permission on that load, so read permission is now required to update or delete an object.
If your checker allowed updating objects the user cannot read, change it accordingly.

Step 4: the repository
----------------------

You do not have to migrate the repository together with the ViewSet. Wrap an existing legacy repository in
:class:`flask_jsonapi.data_services.LegacyRepositoryAdapter` and use it as the ``data_service``:

.. code-block:: python

    from flask_jsonapi import data_services

    class ArticleViewSet(flask_jsonapi.ViewSet):
        ...
        data_service = data_services.LegacyRepositoryAdapter(ArticleRepository())

The adapter calls the repository the way the legacy views did:

.. list-table::
   :header-rows: 1

   * - Data service method
     - Legacy repository call
   * - ``create(data=data)``
     - ``repository.create(data)``
   * - ``read(id=id)``
     - ``repository.get_detail(id)``
   * - ``list(filters=..., sorting=..., pagination=...)``
     - ``repository.get_list(filters, sorting, pagination)`` for the items. ``repository.get_count(filters)`` for
       the total, only when the request asks for a page; otherwise the total is ``None``
   * - ``update(resource=resource, data=data)``
     - ``repository.update({**data, 'id': resource.id})``
   * - ``destroy(resource=resource)``
     - ``repository.delete(resource.id)``

Legacy repositories still fetch the object again inside ``update`` and ``delete``, which is accepted until you
migrate them.

.. warning::

    The adapter returns what the repository returns from ``update``. The legacy SQLAlchemy repository returns the
    object, so ``PATCH`` through the adapter answers **200 with a body**, where the legacy view answered
    **204** with none. Both are valid JSON:API, but clients that expect an empty body must be checked.

When you are ready, move the repository to
``flask_jsonapi.data_services.sqlalchemy_repositories.SqlAlchemyModelRepository`` (see below), or write a data
service of your own, and drop the adapter.

Step 5: raise data service exceptions, not HTTP ones
----------------------------------------------------

Legacy repositories raise HTTP exceptions such as ``ForbiddenError`` and ``ObjectNotFound``. A data service raises
exceptions from :mod:`flask_jsonapi.data_services` and the view turns them into HTTP errors:

.. list-table::
   :header-rows: 1

   * - Before
     - After
   * - ``exceptions.ObjectNotFound``
     - ``data_services.ResourceNotFound``
   * - ``exceptions.ForbiddenError``
     - ``data_services.PermissionDenied``
   * - ``exceptions.AttributeValidationError``
     - ``data_services.InvalidData(detail, field=...)``
   * - ``exceptions.InvalidSort``
     - ``data_services.InvalidSortParameter``
   * - ``exceptions.InvalidFilters``
     - ``data_services.InvalidFilterParameter``
   * - a SQL integrity error reported as ``ForbiddenError``
     - ``data_services.Conflict`` (409)
   * - a database that is down
     - ``data_services.Unavailable`` (503)

The new SQLAlchemy repository does this for you: an ``IntegrityError`` becomes ``Conflict``, an
``OperationalError`` becomes ``Unavailable`` and any other ``SQLAlchemyError`` becomes a plain
``DataServiceException`` (500). A ``JsonApiException`` raised by a legacy repository behind the adapter still
passes through unchanged.

Other differences of the new ``SqlAlchemyModelRepository``:

* ``instance_name`` is gone.
* ``get_detail``, ``get_list`` and ``delete`` are renamed ``read``, ``list`` and ``destroy``, after the actions
  (see the table in step 4). Middlewares and object permissions use the same names. ``get_count`` is gone: ``list``
  returns a ``ListResult`` with the items and, when the request asks for a page, the total. A repository that
  overrode ``get_list`` and ``get_count`` overrides ``list`` and returns both, see :ref:`layers-list-results`.
  ``get_query``, the ``apply_*`` methods, ``build`` and ``update_attribute`` keep theirs.
* ``update(resource=..., data=...)`` and ``destroy(resource=...)`` take the loaded object and never fetch it again.
* All arguments are keyword-only.

.. _migration-errors:

What changes for code you do not migrate
----------------------------------------

Upgrading changes error responses of legacy views, too:

* Every error from a view is now a JSON:API error document, including unexpected exceptions (a generic 500 with
  no internal details, logged with ``logger.exception``) and ``flask.abort()`` (same status and title).
  Errors raised in a ``view_decorators`` decorator are still outside the view and are not converted.
* Flask app error handlers (``@app.errorhandler``) no longer run for exceptions raised inside a flask-jsonapi
  view, because the view turns them into JSON:API errors itself. In testing mode such exceptions no longer reach
  the test client either. Move that handling into a guard or a middleware, or into the view.
* Empty ``detail`` and ``source`` members are omitted from error objects. A test that compares an error body to
  one containing ``'source': {}`` needs updating.
* Exception classes accept keyword arguments. The old positional forms, such as
  ``JsonApiException(source, detail)`` and ``ForbiddenError('detail')``, still work.
