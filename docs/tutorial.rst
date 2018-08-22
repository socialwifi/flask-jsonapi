Tutorial
========

The objective of this tutorial is to demonstrate basic techniques. The next application example will be helpful here.

General overview
----------------

Flask-jsonapi framework is developed for serving data to external world by Flask based application. That means
the application deals with the data source, usually database, called **resource**. Access rules to
resource data are defined throughout **repository** construct, which is an equivalent to the view function in
typical web application. To deal with JSON format the application has to map map data source structure into JSON.
To get all that stuff together application has to define the access point called **endpoint** and tie it to some url to
be ready for external requests.

First application
-----------------

This example is showing each step of developing flask-jsonapi application.

Let say we need to make API for the page with articles, comments and it's authors.
Flask-jsonapi is model independent and could work with data model defined anyhow. In a real life we dealing with particular
databases through ORM of our choice. This tutorial is using SQLAlchemy.

To make our project working we need to start with database definition.

Database definition
~~~~~~~~~~~~~~~~~~~

Database for blog page consists of 3 tables: author, article and comment.
Each Article and Comment has single Author. Article could have many Comments. Such a database is managed by application
via SQLAlchemy.

Repository
~~~~~~~~~~
flask_jsonapi comes with tha *ResourceRepository* base definition and the *SqlAlchemyModelRepository* on top of it.
*ResourceRepository* has defined following access methods:

.. code-block:: python

    def create(self, data, **kwargs)
    def get_list(self, filters=None)
    def get_detail(self, id)
    def delete(self, id)
    def update(self, data, **kwargs)

To work with any particular data source model it is needed to define it's own specific *repository* which should address
the basis like data set instance, querying methods and so on.
To deal with SQLAlchemy *SqlAlchemyModelRepository* has 4 fields, redefines access methods and adds some specific methods
to cope with data.

Fields:
    - ``model`` - points to model definition
    - ``session`` - SQLAlchemy database handler
    - ``instance_name`` - the table instance for the model
    - ``filter_methods_map`` - defines mapping filters into queries

The standard access methods are simply adjusted to work with SQLAlchemy database instance. Two additional methods needs short description:

    - ``build(self, kwargs)`` - creates new model object using data in kwargs, it is called in a ``create()`` method
    - ``get_query(self)`` - simply returns models query

Both function should be overwritten in your application for access rights control or limiting data set size or scope.


Time to define *repository* for posts in **repositories.py** file:

.. code-block:: python

    class AritcleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = models.Article
        instance_name = 'articles'
        session = db.session

        # example of preventing some operations:
        def delete(self, id):
            raise sqlalchemy_repositories.ForbiddenError(detail='Operation forbidden.')

    # create the repository instance
    article_repository = ArticleRepository

Schema
~~~~~~
Here you need to define the format of exposed data in JSON standard. The most important things here are:
    - what fields will be visible for users
    - to properly reflect the relationships in data resource

Please refer to `marshmallow-jsonapi <https://marshmallow-jsonapi.readthedocs.io/en/latest/api_reference.html>`_ for details.

Endpoint
~~~~~~~~
Next step is to setup the endpoints in **endpoints.py** file:

.. code-block:: python

    class PostRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
        schema = schemas.ArticleSchema
        repository = repositories.article_repository
        # if authorisation is needed
        view_decorators = (
            oauth.has_required_scopes,
        )

Routing
~~~~~~~
Finally in **flask_app.py** file we can setup our flask application with JSON API in it:

.. code-block:: python

    from flask_jsonapi.api import Api

    def main():
        app = create_app()
        setup_api(app)
        return app

    # flask app creation
    def create_app():
        .......
        return app

    # the flask_jsonapi part
    def setup_api(app):
        api = Api(app)
        # tie endpoints with urls
        api.repository(endpoints.ArticleRepositoryViewSet(), 'articles', '/articles/')
        api.repository(endpoints.AuthorRepositoryViewSet(), 'authors', '/authors/')

Relationships
~~~~~~~~~~~~~

Each ``Article`` has an ``Author``, which is reflected in a source only on model and schema level:

.. code-block:: python

    # models.py
    author_id = sqlalchemy.Column(sqlalchemy.ForeignKey('author.id'))
    # schemas.py
    author = fields.Relationship(required=True, type_='authors',
                                 attribute='author_id', include_resource_linkage=True)

There is no need to change ``Repository`` or ``RepositoryViewSet`` to reflect One-to-One or One-to-Many relations.
