import flask
import pytest


@pytest.fixture
def app():
    application = flask.Flask(__name__)
    return application


@pytest.fixture
def api(app):
    from flask_jsonapi import api
    application_api = api.Api(app)
    return application_api


@pytest.fixture
def test_client(app):
    with app.test_client() as client:
        yield client
