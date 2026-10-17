Guide
=====

This page shows how to build an API with :class:`flask_jsonapi.ViewSet`: what the design gives you, short recipes
for common tasks and one complete application. :doc:`view_sets`, :doc:`views` and :doc:`layers` are the reference
for every part.

Strong points
-------------

* Each layer has one job and knows nothing about the others.
* The order of the layers is fixed, and one ViewSet declaration shows all of them.
* Allowed actions and guards run before any input is parsed.
* Object permissions have their own slot and always run before every middleware.
* A ViewSet serves nothing it does not declare: ``allowed_actions`` defaults to empty.
* Data services carry no HTTP and can be called from anywhere: tasks, scripts, tests.
* A list and its total come from one call, so every filter a layer adds applies to both.
* Every exception raised in a layer reaches the client as a JSON:API error document, with an honest status and
  no internal details.
* The object of a detail request is loaded once and handed to ``update`` and ``destroy``.
* One declaration can be reused for another audience by subclassing.

A request passes the layers in this order:

.. code-block:: text

    request
      -> headers             406, 415 for a wrong Accept or Content-Type header
      -> allowed actions     405 if the ViewSet does not declare the action
      -> guards              401, 403, ... raised by your checks
      -> parsing             400, 409, 422 for a bad query string or body
      -> object permissions  403 for a call the client has no right to make
      -> middlewares         wrap every call to the data service
      -> data service        loads and stores the data; 404, 409, 422, 503 from its exceptions
    response

See :ref:`layers-request-flow` for the exact steps of every HTTP method.

How to
------

The recipes build on each other. Names that a recipe uses without defining, such as ``ArticleSchema`` or
``ArticleRepository``, are defined in an earlier recipe or in the :ref:`full example <guide-full-example>`.

Serve a read-only resource
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import flask_jsonapi


    class AuthorViewSet(flask_jsonapi.ViewSet):
        schema_class = AuthorSchema
        data_service = AuthorRepository()
        allowed_actions = {flask_jsonapi.Actions.read, flask_jsonapi.Actions.list}


    api = flask_jsonapi.Api(app)
    api.repository(AuthorViewSet(), 'authors', '/authors/')

``GET /authors/`` and ``GET /authors/1/`` are served. ``POST``, ``PATCH`` and ``DELETE`` answer ``405``.

Require authentication
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import flask

    from flask_jsonapi import exceptions
    from flask_jsonapi import guards


    class RequireToken(guards.Guard):
        def check(self, action):
            if not token_is_valid(flask.request.headers.get('Authorization')):
                raise exceptions.Unauthorized(detail='A valid token is required.')

Add it to the ViewSet with ``guards = [RequireToken()]``. ``token_is_valid`` stands for your own check. A request
without a valid token answers ``401`` before its body is read. ``check`` receives the action, for example
``flask_jsonapi.Actions.list``, so a guard can treat reads and writes differently.

Allow a client to see and change only what it owns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from flask_jsonapi import permissions


    class AuthorChecker(permissions.PermissionChecker):
        def check_create_permission(self, *, data):
            return {**data, 'author_id': current_author_id()}

        def check_read_permission(self, *, resource):
            if resource.author_id != current_author_id():
                raise permissions.PermissionException(detail='This article belongs to someone else.')
            return resource

        def check_update_permission(self, *, resource, data):
            return resource, data

        def check_destroy_permission(self, *, resource):
            return resource


    class OwnArticles(permissions.CheckObjectPermission):
        permission_checker = AuthorChecker()

        def apply_permission_filter(self, filters):
            return {**filters, 'author_id': current_author_id()}

Add it with ``object_permissions = OwnArticles()``. ``current_author_id()`` stands for the way your application
identifies the client; it reads the request on every call, because one ``OwnArticles`` instance serves all requests
(see :ref:`view-sets-instances`). A new article gets the client as its author, the list shows only the client's articles
(and the pagination total includes only those), and ``GET``, ``PATCH`` or ``DELETE`` on someone else's article
answers ``403``. The update and delete checks pass the object through, because ``PATCH`` and ``DELETE`` load it
through ``read`` first, which already ran ``check_read_permission``.

``apply_permission_filter`` returns filters that restrict the list to what the client may list. It may also raise
``PermissionException`` when the client's own filters ask for objects it may not list, and the request answers
``403``. ``check_list_permission`` then runs on the listed objects as a safety net: if it drops any, the response
leaves out the total and a warning is logged. See :ref:`layers-permission-filter`.

Require a filter on a list
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import flask_jsonapi

    from flask_jsonapi import middlewares


    class CommentFilterSchema(flask_jsonapi.FilterSchema):
        article_id = flask_jsonapi.FilterField()


    class CommentViewSet(flask_jsonapi.ViewSet):
        schema_class = CommentSchema
        data_service = CommentRepository()
        filter_schema = CommentFilterSchema()
        allowed_actions = {flask_jsonapi.Actions.list}
        middlewares = [middlewares.CheckRequiredListFilters(['article_id'])]

``GET /comments/?filter[article_id]=1`` lists the comments of one article. ``GET /comments/`` answers ``400``
with the detail ``"article_id" filter is required``.

Add a filter from the request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import flask

    from flask_jsonapi import middlewares


    class InClientLanguage(middlewares.Middleware):
        def list(self, *, filters, inner, **kwargs):
            return inner.list(filters=self.with_language(filters), **kwargs)

        @staticmethod
        def with_language(filters):
            language = flask.request.accept_languages.best_match(['en', 'pl'], default='en')
            return {**filters, 'language': language}

The list shows the articles in the language of the ``Accept-Language`` header, and the pagination total includes
only those articles. Build a new dict and leave ``filters`` unchanged.

Record changes
~~~~~~~~~~~~~~

.. code-block:: python

    import logging

    from flask_jsonapi import middlewares

    audit_log = logging.getLogger('audit')


    class RecordChanges(middlewares.Middleware):
        def update(self, *, resource, data, inner):
            before = {key: getattr(resource, key) for key in data}
            result = inner.update(resource=resource, data=data)
            audit_log.info('Article %s changed from %r to %r.', resource.id, before, data)
            return result

If ``inner.update`` raises, the exception propagates and the code after it does not run.
Object permissions run before every middleware, so with ``object_permissions = OwnArticles()`` and
``middlewares = [RecordChanges()]`` a forbidden change stops at ``OwnArticles`` and is never recorded.

Run business logic as a data service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from flask_jsonapi import data_services


    class EmptyArticle(data_services.InvalidData):
        pass


    class PublishArticle(data_services.DataService):
        def __init__(self, repository):
            self.repository = repository

        def read(self, *, id):
            return self.repository.read(id=id)

        def update(self, *, resource, data):
            if not resource.body:
                raise EmptyArticle('An empty article cannot be published.', field='body')
            return self.repository.update(resource=resource, data={'published': True})

Serve it from its own ViewSet:

.. code-block:: python

    class ArticlePublicationViewSet(flask_jsonapi.ViewSet):
        schema_class = ArticleSchema
        data_service = PublishArticle(ArticleRepository())
        allowed_actions = {flask_jsonapi.Actions.update}
        guards = [RequireToken()]
        object_permissions = OwnArticles()


    api.repository(ArticlePublicationViewSet(), 'article_publications', '/article-publications/')

``PATCH /article-publications/1/`` publishes the article, or answers ``422`` with ``source.pointer`` set to
``/data/attributes/body``. The view picks the status from the base class of the exception, see
:ref:`layers-errors`. ``PublishArticle`` touches no HTTP, so a script or a task can call it directly:
``PublishArticle(ArticleRepository()).update(resource=article, data={})``.

.. _guide-list-source:

Serve a list from a source of your own
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from flask_jsonapi import data_services


    class ArticleSearch(data_services.DataService):
        def __init__(self, index):
            self.index = index

        def list(self, *, filters, sorting, pagination):
            hits = self.index.search(filters.get('text', ''), sorting)
            if not pagination:
                return data_services.ListResult(hits, total=None)
            start = (pagination['number'] - 1) * pagination['size']
            return data_services.ListResult(hits[start:start + pagination['size']], total=len(hits))

``index`` stands for a search index of your own. ``list`` returns a ``ListResult`` with the objects of the page and
the number of all matches. Set the total whenever the request asks for a page: the list view builds the ``last``
link from it. With ``total=None`` the ``last`` link is ``null``, and ``next`` is present only after a full page.

Compute a field for the response
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from marshmallow_jsonapi import Schema
    from marshmallow_jsonapi import fields


    class ArticleSchema(Schema):
        id = fields.Int(as_string=True)
        title = fields.Str(required=True)
        body = fields.Str()
        word_count = fields.Method('count_words', dump_only=True)

        class Meta:
            type_ = 'articles'

        def count_words(self, article):
            return len((article.body or '').split())

``word_count`` is dump-only: responses include it and requests cannot set it. The schema computes it once per
object in the response, so middlewares and data services never deal with presentation.

Expose the same resource to another audience
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class InternalArticleViewSet(ArticleViewSet):
        allowed_actions = {*ArticleViewSet.allowed_actions, flask_jsonapi.Actions.destroy}
        guards = []
        object_permissions = None


    api.repository(ArticleViewSet(), 'articles', '/articles/')
    api.repository(InternalArticleViewSet(), 'internal_articles', '/internal/articles/')

The internal endpoint serves other services of your network, so expose it only there. It keeps the schema, the
filters, the middlewares and the data service, asks for no token, shows every article and adds ``DELETE``. A
subclass replaces ``allowed_actions``, ``guards``, ``object_permissions`` and ``middlewares``; nothing is merged,
and what it does not set it inherits. To extend an inherited list, write it out:
``middlewares = [*ArticleViewSet.middlewares, RecordChanges()]``.

Use the SQLAlchemy repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from flask_jsonapi.data_services import sqlalchemy_repositories


    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = session

        def get_query(self):
            return super().get_query().filter(Article.deleted_at.is_(None))

``read`` and ``list`` both start from ``get_query``, so a deleted article is not
listed, not part of a total and not found. Every write takes a ``strategy``, ``'commit'`` by default:

.. code-block:: python

    articles = ArticleRepository()
    revisions = RevisionRepository()

    article = articles.create(data={'title': 'Draft'}, strategy='flush')
    revisions.create(data={'article_id': article.id, 'title': article.title})

``'flush'`` sends the insert and assigns ``article.id`` without committing. The second write commits both,
because both repositories use the same session (``RevisionRepository`` is another repository on it). Database
errors become data service exceptions, for example a unique constraint violation becomes ``Conflict`` and answers
``409``.

.. _guide-full-example:

Full example
------------

A complete application with two resources, authors and articles. Every client with a token can read authors and
articles. A client creates articles as their author, and only the author can change an article. Articles cannot be
deleted.

.. literalinclude:: examples/full_example.py
    :language: python

The parts, from the top:

* ``Author`` and ``Article`` are SQLAlchemy models; an article belongs to an author. ``ArticleSchema`` dumps the
  author as a relationship, so ``GET /articles/1/?include=author`` includes it.
* ``current_author_id()`` identifies the client by the ``Authorization: Bearer <token>`` header. The tokens are
  fixed for the example.
* ``RequireToken`` is a guard: a request without a known token answers ``401``.
* ``AuthorPermissions`` is a ``CheckObjectPermission`` with the ``AuthorCanChange`` checker, set as the
  ``object_permissions`` of ``ArticleViewSet``. A new article gets the client as its author, and ``PATCH`` by anyone
  else answers ``403``. Every article is readable, so ``apply_permission_filter`` adds no filter.
* ``AuthorViewSet`` serves reads only. ``ArticleViewSet`` serves create, read, list and update, not delete.
* ``ArticleSchema`` loads ``data.id``, so a client may choose an article's id on ``POST``. An id that is already
  in use answers ``409``.
* ``remove_session`` closes the session at the end of every request.

Install the library with SQLAlchemy support and run the file:

.. code-block:: bash

    pip install 'flask-jsonapi[sqlalchemy]'
    python full_example.py

An ``Accept`` header, when present, must be exactly ``application/vnd.api+json`` (``406`` otherwise). curl sends
``Accept: */*`` by default, so the requests below set it. ``POST`` and ``PATCH`` also need
``Content-Type: application/vnd.api+json`` (``415`` otherwise).
The responses below are formatted for reading.

A request without a token:

.. code-block:: bash

    curl -H 'Accept: application/vnd.api+json' http://localhost:5000/articles/

``401 Unauthorized``:

.. code-block:: json

    {
        "errors": [
            {
                "status": 401,
                "title": "Unauthorized",
                "detail": "A valid bearer token is required."
            }
        ],
        "jsonapi": {
            "version": "1.0"
        }
    }

Alice creates an article:

.. code-block:: bash

    curl -H 'Accept: application/vnd.api+json' \
        -H 'Content-Type: application/vnd.api+json' \
        -H 'Authorization: Bearer alice-token' \
        http://localhost:5000/articles/ \
        --data '{"data": {"type": "articles", "attributes": {"title": "Hello", "body": "First post."}}}'

``201 Created``:

.. code-block:: json

    {
        "data": {
            "type": "articles",
            "id": "1",
            "attributes": {
                "title": "Hello",
                "body": "First post."
            },
            "relationships": {
                "author": {
                    "data": {
                        "type": "authors",
                        "id": "1"
                    }
                }
            }
        },
        "jsonapi": {
            "version": "1.0"
        }
    }

Bob lists the articles:

.. code-block:: bash

    curl -H 'Accept: application/vnd.api+json' \
        -H 'Authorization: Bearer bob-token' \
        http://localhost:5000/articles/

``200 OK``:

.. code-block:: json

    {
        "data": [
            {
                "type": "articles",
                "id": "1",
                "attributes": {
                    "title": "Hello",
                    "body": "First post."
                },
                "relationships": {
                    "author": {
                        "data": {
                            "type": "authors",
                            "id": "1"
                        }
                    }
                }
            }
        ],
        "meta": {
            "count": 1
        },
        "jsonapi": {
            "version": "1.0"
        }
    }

Bob asks for the first page, one article per page (``-g`` stops curl from reading the brackets as a pattern):

.. code-block:: bash

    curl -g -H 'Accept: application/vnd.api+json' \
        -H 'Authorization: Bearer bob-token' \
        'http://localhost:5000/articles/?page[size]=1&page[number]=1'

``200 OK``, with the pagination links built from the total. There is only one article, so ``next`` is ``null``
and ``last`` is the first page:

.. code-block:: json

    {
        "data": [
            {
                "type": "articles",
                "id": "1",
                "attributes": {
                    "title": "Hello",
                    "body": "First post."
                },
                "relationships": {
                    "author": {
                        "data": {
                            "type": "authors",
                            "id": "1"
                        }
                    }
                }
            }
        ],
        "links": {
            "self": "http://localhost:5000/articles/?page[size]=1&page[number]=1",
            "first": "http://localhost:5000/articles/?page[size]=1&page[number]=1",
            "previous": null,
            "next": null,
            "last": "http://localhost:5000/articles/?page[size]=1&page[number]=1"
        },
        "meta": {
            "count": 1
        },
        "jsonapi": {
            "version": "1.0"
        }
    }

Bob tries to change Alice's article:

.. code-block:: bash

    curl -X PATCH \
        -H 'Accept: application/vnd.api+json' \
        -H 'Content-Type: application/vnd.api+json' \
        -H 'Authorization: Bearer bob-token' \
        http://localhost:5000/articles/1/ \
        --data '{"data": {"type": "articles", "id": "1", "attributes": {"title": "Mine now"}}}'

``403 Forbidden``, and the article keeps its title:

.. code-block:: json

    {
        "errors": [
            {
                "status": 403,
                "title": "Forbidden",
                "detail": "Only the author can change an article."
            }
        ],
        "jsonapi": {
            "version": "1.0"
        }
    }

Alice tries to delete her article, which ``ArticleViewSet`` does not declare:

.. code-block:: bash

    curl -X DELETE \
        -H 'Accept: application/vnd.api+json' \
        -H 'Authorization: Bearer alice-token' \
        http://localhost:5000/articles/1/

``405 Method Not Allowed``:

.. code-block:: json

    {
        "errors": [
            {
                "status": 405,
                "title": "Method not allowed",
                "detail": "Delete is not allowed for this resource"
            }
        ],
        "jsonapi": {
            "version": "1.0"
        }
    }

These requests and responses are checked by ``tests/test_docs_full_example.py``.
