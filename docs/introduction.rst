Introduction
++++++++++++

The lightweight applications (those one based on Flask) needs to use JSON too.
That's why we've made this framework. Please enjoy.

Requirements
++++++++++++

This package requires at least python 3.5 and following packages:

- Flask
- marshmallow
- marshmallow_jsonapi

Installation
++++++++++++

This package requires at least python 3.5.
To install run::

    pip install flask-jsonapi

Simple application
++++++++++++++++++

Run in python::

    import collections

    import flask
    import marshmallow_jsonapi

    import flask_jsonapi
    from flask_jsonapi import exceptions

    class ExampleSchema(marshmallow_jsonapi.Schema):
        id = marshmallow_jsonapi.fields.UUID()
        body = marshmallow_jsonapi.fields.Str()

        class Meta:
            type_ = 'example'
            strict = True

    ExampleModel = collections.namedtuple('ExampleModel', 'id body')

    repository = {
        'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4':
            ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
                         body='stop'),
        'f60717a3-7dc2-4f1a-bdf4-f2804c3127a5':
            ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5',
                         body='hammer'),
    }

    app = flask.Flask(__name__)

    class ExampleListView(flask_jsonapi.ResourceList):
        schema = ExampleSchema

        def read_many(self, filters):
            return list(repository.values())

        def create(self, data):
            id = data.get('id') or str(uuid.uuid4())
            if id in repository:
                raise exceptions.JsonApiException
            obj = ExampleModel(id=id, body=data['body'])
            repository[id] = obj
            return obj

    class ExampleDetailView(flask_jsonapi.ResourceDetail):
        schema = ExampleSchema

        def read(self, id):
            if id not in repository:
                raise exceptions.ObjectNotFound
            return repository[id]

        def update(self, id, data):
            if id != data.pop('id', id):
                raise exceptions.JsonApiException
            obj = repository[id]
            obj_dict = obj._asdict()
            obj_dict.update(data)
            repository[id] = ExampleModel(**obj_dict)

        def destroy(self, id):
            if id in repository:
                del repository[id]

    application_api = flask_jsonapi.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')

    app.run(host='127.0.0.1', port=5000)

And test it::

    $ curl -H 'Content-Type: application/vnd.api+json' \
        http://localhost:5000/examples/ \
        --data '{"data": {"attributes": {"body": "time"}, "type": "example"}}' 2>/dev/null | python -m json.tool
    {
        "data": {
            "attributes": {
                "body": "time"
            },
            "id": "77e23a62-7c49-4d0f-bb75-3ae5519226f5",
            "type": "example"
        },
        "jsonapi": {
            "version": "1.0"
        }
    }
    $ curl http://localhost:5000/examples/ 2>/dev/null | python -m json.tool
    {
        "data": [
            {
                "attributes": {
                    "body": "stop"
                },
                "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a4",
                "type": "example"
            },
            {
                "attributes": {
                    "body": "time"
                },
                "id": "77e23a62-7c49-4d0f-bb75-3ae5519226f5",
                "type": "example"
            },
            {
                "attributes": {
                    "body": "hammer"
                },
                "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a5",
                "type": "example"
            }
        ],
        "jsonapi": {
            "version": "1.0"
        },
        "meta": {
            "count": 3
        }
    }

Running tests
+++++++++++++

To run tests::

    virtualenv -p python3.6 ~/flask-jsonapi-virtualenv
    . ~/flask-jsonapi-virtualenv/bin/activate
    pip install -r base_requirements.txt
    pip install -U pytest==3.0.5
    pytest

Tutorial
++++++++

Just to make your life easier let's start to write simple application using flask-jsonapi.

General overview
----------------

Flask-jsonapi framework is developed for serving data to external world by Flask based application. That means
the application deals with the some data source, usually database,called **resource**. Access rules to
resource data are defined throughout **repository** construct. Which is somehow an equivalent to the view function in
typical web application. To deal with JSON format it is needed to map data source structure into JSON. Marshmallow-jsonapi
**Schema** is used here. To get all that stuff together we need to define the access point called **endpoint**.
Finally our endpoint needs to be tided to some url to be ready for external requests.

First application
-----------------

Time for the project called *fj_sample*. The objective is to show few basic techniques and step by step adding new functionality.
Let say we need to make API for simple blog which have posts and it's authors.
Flask-jsonapi is model independent and could work with data model defined anyhow. In a real life we dealing with particular
databases through ORM of our choice. In case of this tutorial it is SQLAlchemy. To make our project working we need to start
with database definition, sorry flask-jsonapi will start soon.

Database definition
===================

Below example assumes that we deal we simple database for blog page which consists of 3 tables: user, post and comment.
Each Post and Comment has single author (User). Post could have many comments. Such a database is managed by application
via SQLAlchemy.

Repository
==========
flsk_jsonapi contains definition of general purposes *ResourceRepository* and based on it *SqlAlchemyModelRepository*.
*ResourceRepository* has defined following access methods::

    def create(self, data, **kwargs):
    def get_list(self, filters=None):
    def get_detail(self, id):
    def delete(self, id):
    def update(self, data, **kwargs):

To work with any particular data source model it is needed to define it's own specific *repository* which should address
how to deal with such kind of data (ie. data set instance, quering methods and so on). Flask_jsonapi comes with a repository for SQLAlchemy based models.
*SqlAlchemyModelRepository* has 4 new fields, redefines access methods and adds some specific methods to cope with data.
Let's walk through, starting from fields:

    - ``model`` - points to model definition
    - ``session`` - SQLAlchemy database handler
    - ``instance_name`` - the table instance for the model
    - ``filter_methods_map`` - defines mapping filters into queries

The standard access methods are simply adjusted to work with SQLAlchemy database instance. Two additional methods needs short description:

    - ``build(self, kwargs)`` - creates new model object using data in kwargs, it is called in a ``create()`` method
    - ``get_query(self)`` - simply returns models query

Both function should be overwritten in your application for access rights control or limiting data set size or scope.


Getting back to our application we need to define *repository* for posts in **repositories.py** file::

    class PostRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = models.Post
        instance_name = 'post'
        session = db.session

        # example of preventing some operations:
        def delete(self, id):
            raise sqlalchemy_repositories.ForbiddenError(detail='Operation forbidden.')

    # create the repository instance
    post_repository = PostRepository

Schema
======
Here you need to define the format of exposed data in JSON standard. The most important things here are:
    - what fields will be visible for users
    - to properly reflect the relationships in data resource
Please refer to `marshmallow-jsonapi <https://marshmallow-jsonapi.readthedocs.io/en/latest/api_reference.html>`_ for details.

Endpoint
========
Next step is to setup the endpoints in **endpoints.py** file::

    class PostRepositoryViewSet(resource_repository_views.ResourceRepositoryViewSet):
        schema = schemas.PostSchema
        repository = repositories.post_repository
        # if authorisation is needed
        view_decorators = (
            oauth.has_required_scopes,
        )

Routing
=======
Finally in **flask_app.py** file we can setup our flask application with JSON API in it::

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
        api.repository(endpoints.PostRepositoryViewSet(), 'post', '/posts/')
        api.repository(endpoints.UserRepositoryViewSet(), 'user', '/users/')

