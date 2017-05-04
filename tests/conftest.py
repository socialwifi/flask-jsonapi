import flask
import pytest


@pytest.fixture
def app():
    application = flask.Flask(__name__)
    return application
