ViewSets
========

.. versionadded:: 1.5.0

A :class:`flask_jsonapi.ViewSet` declares one resource: its schema, its filters, the actions it serves, the guards,
object permissions and middlewares around the data, and the data service that stores it. Nothing depends on a hidden
convention; everything the endpoint does is visible in the class body. The :doc:`layers` page explains each part.

.. note::

    ``ResourceRepositoryViewSet``, ``ProtectedViewSet`` and their views are deprecated since 1.5.0. They keep
    working. See :doc:`migration` for moving an endpoint to ``ViewSet``.

Declaring a ViewSet
-------------------

.. code-block:: python

    import flask_jsonapi


    class ArticleViewSet(flask_jsonapi.ViewSet):
        schema_class = ArticleSchema
        filter_schema = ArticleFilterSchema()
        allowed_actions = {
            flask_jsonapi.Actions.read,
            flask_jsonapi.Actions.list,
            flask_jsonapi.Actions.update,
        }
        guards = [CheckApiToken()]
        object_permissions = OwnArticles()
        middlewares = [LogRetitles()]
        data_service = ArticleRepository()

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - ``schema_class``
     - The marshmallow-jsonapi schema class of the resource. Required.
   * - ``data_service``
     - The :ref:`data service <layers-data-services>` that stores the resource. Required.
   * - ``filter_schema``
     - A ``FilterSchema`` instance that parses the ``filter[...]`` query parameters of the list view. Defaults to
       a schema without filters.
   * - ``allowed_actions``
     - The set of ``flask_jsonapi.Actions`` the ViewSet serves. Defaults to empty: a ViewSet that does not
       declare it serves nothing.
   * - ``guards``
     - Request-level checks, run in order before the body is parsed. Defaults to empty.
   * - ``object_permissions``
     - The object permission layer, outermost in the pipeline, see :doc:`layers`. Defaults to ``None``: no layer.
   * - ``middlewares``
     - Wrappers around the data service calls, outermost first, inside the object permissions. Defaults to empty.
   * - ``view_decorators``
     - Decorators applied to the Flask view functions, for Flask-level integration only. Defaults to empty.
   * - ``detail_view_class``, ``list_view_class``
     - The view classes. Default to :class:`flask_jsonapi.DetailView` and :class:`flask_jsonapi.ListView`.

Register it with :class:`flask_jsonapi.Api`, one ViewSet per resource:

.. code-block:: python

    api = flask_jsonapi.Api(app)
    api.repository(ArticleViewSet(), 'articles', '/articles/')

This registers a list view under ``/articles/`` and a detail view under ``/articles/<id>/``.

.. _view-sets-instances:

Instances and classes
---------------------

An attribute holds a class when the view must create a new object for every request, with arguments taken from the
request. Their names end in ``_class``:

* ``schema_class``: the view creates a schema for every request, with the ``include`` and ``fields`` of the query
  string, or with ``partial=True`` for ``PATCH``.
* ``detail_view_class`` and ``list_view_class``: Flask creates a view object for every request.

Every layer holds an instance: ``filter_schema``, each of the ``guards``, ``object_permissions``, each of the
``middlewares`` and ``data_service``. Each one is created once, when the module that declares the ViewSet is
imported, and is shared by all requests and all threads. So these instances must not keep per-request state on
``self``:

* Read the client from ``flask.request`` or ``flask.g`` in the method that needs it, on every call. Never store it
  in an attribute: a request in another thread would read or overwrite it.
* Keep values that belong to one request in local variables, or on ``flask.g``, which Flask creates anew for every
  request.
* Use a database session scoped to the thread or the request, such as SQLAlchemy's ``scoped_session``, as the
  :ref:`full example <guide-full-example>` does.

.. code-block:: python

    class LogReads(middlewares.Middleware):
        def read(self, *, id, inner):
            author_id = current_author_id()
            resource = inner.read(id=id)
            logger.info('Author %s read article %s.', author_id, id)
            return resource

``author_id`` is a local variable. Stored as ``self.author_id``, it could be overwritten by a request in another
thread between the assignment and its use.

Reuse by subclassing
--------------------

``guards``, ``object_permissions``, ``middlewares`` and ``allowed_actions`` are plain class attributes. A subclass
replaces them, they are not merged. That makes one definition reusable for several APIs: here the same resource is
served to clients with a token and, without one, to other services in the same network.

.. code-block:: python

    class InternalArticleViewSet(ArticleViewSet):
        allowed_actions = {
            flask_jsonapi.Actions.create,
            flask_jsonapi.Actions.read,
            flask_jsonapi.Actions.list,
            flask_jsonapi.Actions.update,
            flask_jsonapi.Actions.destroy,
        }
        guards = []
        object_permissions = None
        middlewares = []


    api.repository(ArticleViewSet(), 'articles', '/articles/')
    api.repository(InternalArticleViewSet(), 'internal_articles', '/internal/articles/')

The internal ViewSet inherits the schema, the filters and the data service. It switches off the token guard and
the object permissions explicitly, so serve it only where clients from outside cannot reach it. A subclass that does
not set ``allowed_actions`` inherits them.

To add to the inherited list instead of replacing it, say so explicitly:

.. code-block:: python

    class AuditedArticleViewSet(ArticleViewSet):
        middlewares = [*ArticleViewSet.middlewares, AuditChanges()]

Data services
-------------

``data_service`` is an instance of any class with the :class:`flask_jsonapi.data_services.DataService` methods,
see :doc:`layers`: ``create``, ``read``, ``list``, ``update`` and ``destroy``. ``list`` returns a ``ListResult``
with the items and, when the request asks for a page, their total, see :ref:`layers-list-results`. One instance
is shared by all requests, so keep per-request state out of it, see :ref:`view-sets-instances`.

An existing legacy repository can be used through
:class:`flask_jsonapi.data_services.LegacyRepositoryAdapter`, see :doc:`migration`.
