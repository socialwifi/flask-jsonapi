import flask
import pytest
import sqlalchemy

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URI = 'sqlite://'


@pytest.fixture
def app():
    application = flask.Flask(__name__)
    return application


@pytest.fixture
def db_engine():
    return sqlalchemy.create_engine(TEST_DATABASE_URI)


@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = scoped_session(sessionmaker(bind=db_engine))
    yield session
    session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture
def setup_db_schema(request, db_engine, db_session):
    model_base = request.param
    model_base.query = db_session.query_property()
    model_base.metadata.create_all(db_engine)
    yield
    model_base.metadata.drop_all(db_engine)
