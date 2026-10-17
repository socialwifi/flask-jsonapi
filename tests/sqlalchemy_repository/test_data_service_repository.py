import contextlib
import logging

from unittest import mock

import pytest
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm

from flask_jsonapi.data_services import exceptions
from flask_jsonapi.data_services import sqlalchemy_repositories

Base = sqlalchemy.orm.declarative_base()


class Article(Base):
    __tablename__ = 'articles'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String, unique=True)


@pytest.fixture
def repository(db_session):
    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        session = db_session

    return ArticleRepository()


def repository_log_records(caplog):
    return [record for record in caplog.records if record.name == sqlalchemy_repositories.logger.name]


@contextlib.contextmanager
def recorded_statements(engine):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    sqlalchemy.event.listen(engine, 'before_cursor_execute', record)
    try:
        yield statements
    finally:
        sqlalchemy.event.remove(engine, 'before_cursor_execute', record)


@contextlib.contextmanager
def spy_on_with_for_update():
    real = sqlalchemy.orm.Query.with_for_update
    with mock.patch.object(sqlalchemy.orm.Query, 'with_for_update', autospec=True, side_effect=real) as spy:
        yield spy


@contextlib.contextmanager
def concurrent_insert_before_flush(repository, engine, **row):
    """Another transaction inserts the row between our lookup and our insert.

    The unique violation is real and happens where PostgreSQL raises it, when the savepoint block flushes. Only the
    message is rewritten to PostgreSQL's wording, which the repository matches on and SQLite does not produce.
    """
    original_build = repository.build

    def build_after_competing_insert(data):
        repository.session.execute(sqlalchemy.insert(Article).values(**row))
        return original_build(data)

    def with_postgres_message(context):
        if 'UNIQUE constraint failed' in str(context.original_exception):
            postgres_error = Exception('duplicate key value violates unique constraint "articles_key"')
            return sqlalchemy.exc.IntegrityError(context.statement, context.parameters, postgres_error)

    sqlalchemy.event.listen(engine, 'handle_error', with_postgres_message)
    try:
        with mock.patch.object(repository, 'build', side_effect=build_after_competing_insert):
            yield
    finally:
        sqlalchemy.event.remove(engine, 'handle_error', with_postgres_message)


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestDataServiceRepository:
    def test_read_of_missing_row_raises_resource_not_found(self, repository):
        with pytest.raises(exceptions.ResourceNotFound):
            repository.read(id=404)

    def test_update_uses_given_resource_without_selecting(self, repository, db_engine, db_session):
        article = repository.create(data={'title': 'old'})
        db_session.refresh(article)
        with recorded_statements(db_engine) as statements:
            updated = repository.update(resource=article, data={'title': 'new'})
        assert not [s for s in statements if s.lstrip().upper().startswith('SELECT')]
        assert updated.title == 'new'

    def test_destroy_deletes_given_resource(self, repository):
        article = repository.create(data={'title': 'gone'})
        repository.destroy(resource=article)
        assert repository.list().items == []

    def test_list_applies_filters_to_items_and_total(self, repository):
        repository.create(data={'title': 'a'})
        repository.create(data={'title': 'b'})
        result = repository.list(filters={'title': 'b'}, pagination={'size': 10, 'number': 1})
        assert ([a.title for a in result.items], result.total) == (['b'], 1)

    def test_unpaginated_list_has_no_total_and_does_not_count(self, repository, db_engine):
        repository.create(data={'title': 'a'})
        with recorded_statements(db_engine) as statements:
            result = repository.list()
        assert ([a.title for a in result.items], result.total) == (['a'], None)
        assert len(statements) == 1
        assert 'count(' not in statements[0].lower()

    def test_paginated_list_counts_and_slices_one_filtered_query(self, repository, db_engine):
        for title in ['ab', 'ac', 'ad', 'bc']:
            repository.create(data={'title': title})
        repository.filter_methods_map = {'title_prefix': lambda value: Article.title.startswith(value)}
        with mock.patch.object(repository, 'apply_filters', wraps=repository.apply_filters) as apply_filters, \
                recorded_statements(db_engine) as statements:
            result = repository.list(
                filters={'title_prefix': 'a'}, sorting=['-title'], pagination={'size': 2, 'number': 2})
        assert ([a.title for a in result.items], result.total) == (['ab'], 3)
        assert apply_filters.call_count == 1
        count_statements = [s for s in statements if 'count(' in s.lower()]
        assert len(statements) == 2
        assert len(count_statements) == 1
        assert 'ORDER BY' not in count_statements[0].upper()

    def test_invalid_sort_raises_invalid_sort_parameter(self, repository):
        with pytest.raises(exceptions.InvalidSortParameter):
            repository.list(sorting=['nonexistent'])

    def test_invalid_filter_raises_invalid_filter_parameter(self, repository):
        with pytest.raises(exceptions.InvalidFilterParameter):
            repository.list(filters={'nonexistent': 1})

    def test_duplicate_raises_conflict_and_session_stays_usable(self, repository):
        repository.create(data={'title': 'same'})
        with pytest.raises(exceptions.Conflict):
            repository.create(data={'title': 'same'})
        assert repository.create(data={'title': 'other'}).title == 'other'

    def test_conflict_is_logged_as_info_without_parameters(self, repository, caplog):
        caplog.set_level(logging.DEBUG)
        repository.create(data={'title': 'secret title'})
        with pytest.raises(exceptions.Conflict):
            repository.create(data={'title': 'secret title'})
        records = repository_log_records(caplog)
        assert [record.levelno for record in records] == [logging.INFO]
        assert 'secret title' not in records[0].getMessage()
        assert records[0].exc_info is None

    def test_operational_error_raises_unavailable_and_rolls_back(self, repository, caplog):
        error = sqlalchemy.exc.OperationalError('x', {}, Exception())
        with mock.patch.object(repository.session, 'commit', side_effect=error), \
                mock.patch.object(repository.session, 'rollback') as rollback:
            with pytest.raises(exceptions.Unavailable):
                repository.create(data={'title': 'a'})
        assert rollback.called
        records = repository_log_records(caplog)
        assert [record.levelno for record in records] == [logging.WARNING]
        assert records[0].exc_info

    def test_failed_read_rolls_back(self, repository):
        error = sqlalchemy.exc.OperationalError('x', {}, Exception())
        with mock.patch.object(repository, 'apply_filters', side_effect=error), \
                mock.patch.object(repository.session, 'rollback') as rollback:
            with pytest.raises(exceptions.Unavailable):
                repository.list()
        assert rollback.called

    @pytest.mark.parametrize(argnames='call, patched, expected', argvalues=[
        (lambda repository: repository.read(id='not-a-number'), 'get_query', exceptions.ResourceNotFound),
        (lambda repository: repository.list(), 'apply_filters', exceptions.InvalidFilterParameter),
        (lambda repository: repository.create(data={'title': 'a'}), 'build', exceptions.InvalidData),
        (lambda repository: repository.update(resource=Article(), data={'title': 'a'}), 'update_attribute',
         exceptions.InvalidData),
    ], ids=['read', 'list', 'create', 'update'])
    def test_data_error_is_translated_by_method_and_rolls_back(self, repository, caplog, call, patched, expected):
        caplog.set_level(logging.DEBUG)
        error = sqlalchemy.exc.DataError('SELECT secret', {'id': 'secret value'}, Exception('invalid input'))
        with mock.patch.object(repository, patched, side_effect=error), \
                mock.patch.object(repository.session, 'rollback') as rollback:
            with pytest.raises(expected) as error_info:
                call(repository)
        assert type(error_info.value) is expected
        assert rollback.called
        assert 'secret' not in str(error_info.value.detail)
        records = repository_log_records(caplog)
        assert [record.levelno for record in records] == [logging.INFO]
        assert 'secret' not in records[0].getMessage()
        assert records[0].exc_info is None

    def test_other_database_error_raises_generic_exception_without_logging(self, repository, caplog):
        caplog.set_level(logging.DEBUG)
        error = sqlalchemy.exc.SQLAlchemyError('x')
        with mock.patch.object(repository.session, 'commit', side_effect=error):
            with pytest.raises(exceptions.DataServiceException) as error_info:
                repository.create(data={'title': 'a'})
        assert type(error_info.value) is exceptions.DataServiceException
        assert repository_log_records(caplog) == []

    def test_update_or_create_refreshes_loaded_objects(self, repository):
        article = repository.create(data={'title': 'old'}, strategy='flush')
        repository.update_or_create(update_data={'title': 'new'}, strategy='flush', id=article.id)
        assert article.title == 'new'

    def test_list_applies_custom_filter_methods(self, repository):
        repository.filter_methods_map = {'title_prefix': lambda value: Article.title.startswith(value)}
        repository.create(data={'title': 'ab'})
        repository.create(data={'title': 'ac'})
        repository.create(data={'title': 'bc'})
        result = repository.list(filters={'title_prefix': 'a'}, pagination={'size': 10, 'number': 1})
        assert (sorted(a.title for a in result.items), result.total) == (['ab', 'ac'], 2)
        assert [a.title for a in repository.list(filters={'title_prefix': 'a', 'title': 'ac'}).items] == ['ac']


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestGetOrCreate:
    def test_returns_existing_row_without_inserting(self, repository, db_engine):
        existing = repository.create(data={'title': 'a'})
        with recorded_statements(db_engine) as statements:
            found = repository.get_or_create(title='a', create_data={'id': 99})
        assert found is existing
        assert not [s for s in statements if s.lstrip().upper().startswith('INSERT')]
        assert len(repository.list().items) == 1

    def test_creates_row_from_lookup_kwargs_and_create_data(self, repository):
        created = repository.get_or_create(title='a', create_data={'id': 7})
        assert (created.id, created.title) == (7, 'a')
        assert [a.id for a in repository.list().items] == [7]

    def test_creates_row_without_create_data(self, repository):
        created = repository.get_or_create(title='a')
        assert created.title == 'a'
        assert len(repository.list().items) == 1

    def test_commits_by_default(self, repository):
        with mock.patch.object(repository.session, 'commit', wraps=repository.session.commit) as commit:
            repository.get_or_create(title='a')
        assert commit.called

    def test_flush_strategy_does_not_commit(self, repository):
        with mock.patch.object(repository.session, 'commit') as commit:
            created = repository.get_or_create(title='a', strategy='flush')
        assert not commit.called
        assert created.id is not None
        assert len(repository.list().items) == 1

    def test_for_update_returns_existing_row_and_requests_the_lock(self, repository):
        existing = repository.create(data={'title': 'a'})
        with spy_on_with_for_update() as with_for_update:
            assert repository.get_or_create(title='a', for_update=True) is existing
        assert with_for_update.call_count == 1

    def test_for_update_creates_missing_row_and_requests_the_lock(self, repository):
        with spy_on_with_for_update() as with_for_update:
            created = repository.get_or_create(title='a', for_update=True)
        assert created.title == 'a'
        assert len(repository.list().items) == 1
        assert with_for_update.call_count == 1

    def test_lock_is_not_requested_by_default(self, repository):
        with spy_on_with_for_update() as with_for_update:
            repository.get_or_create(title='a')
        assert not with_for_update.called

    def test_create_data_wins_over_lookup_kwargs(self, repository):
        created = repository.get_or_create(title='lookup', create_data={'title': 'created'})
        assert created.title == 'created'

    def test_duplicate_key_race_returns_row_found_by_second_lookup(self, repository, db_engine):
        with concurrent_insert_before_flush(repository, db_engine, title='a'):
            found = repository.get_or_create(title='a', strategy='flush')
        assert found.title == 'a'
        assert len(repository.list().items) == 1

    def test_other_integrity_error_is_translated_to_conflict(self, repository):
        repository.create(data={'title': 'taken'})
        with pytest.raises(exceptions.Conflict):
            repository.get_or_create(id=7, create_data={'title': 'taken'})
        assert repository.get_or_create(title='c').title == 'c'

    def test_data_error_is_translated_and_rolls_back(self, repository):
        error = sqlalchemy.exc.DataError('SELECT secret', {}, Exception('invalid input'))
        with mock.patch.object(repository, 'build', side_effect=error), \
                mock.patch.object(repository.session, 'rollback') as rollback:
            with pytest.raises(exceptions.InvalidData) as error_info:
                repository.get_or_create(title='a')
        assert rollback.called
        assert 'secret' not in str(error_info.value.detail)


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestUpdateOrCreate:
    def test_plain_update_of_matching_row_returns_none(self, repository):
        article = repository.create(data={'title': 'old'})
        result = repository.update_or_create(update_data={'title': 'new'}, id=article.id)
        assert result is None
        assert [a.title for a in repository.list().items] == ['new']

    def test_creates_row_from_lookup_kwargs_and_update_data_when_nothing_matches(self, repository):
        created = repository.update_or_create(update_data={'title': 'a'}, id=7)
        assert (created.id, created.title) == (7, 'a')
        assert len(repository.list().items) == 1

    def test_commits_by_default_on_update_and_on_create(self, repository):
        article = repository.create(data={'title': 'old'})
        with mock.patch.object(repository.session, 'commit', wraps=repository.session.commit) as commit:
            repository.update_or_create(update_data={'title': 'new'}, id=article.id)
            assert commit.call_count == 1
            repository.update_or_create(update_data={'title': 'a'}, id=article.id + 1)
            assert commit.call_count == 2

    def test_flush_strategy_does_not_commit(self, repository):
        with mock.patch.object(repository.session, 'commit') as commit:
            created = repository.update_or_create(update_data={'title': 'a'}, strategy='flush', id=7)
            repository.update_or_create(update_data={'title': 'b'}, strategy='flush', id=7)
        assert not commit.called
        assert created.id == 7
        assert [a.title for a in repository.list().items] == ['b']

    def test_update_data_wins_over_lookup_kwargs_on_create(self, repository):
        created = repository.update_or_create(update_data={'id': 8}, id=7)
        assert created.id == 8

    def test_duplicate_key_race_updates_instead(self, repository, db_engine):
        with concurrent_insert_before_flush(repository, db_engine, id=7, title='inserted by another transaction'):
            repository.update_or_create(update_data={'title': 'a'}, strategy='flush', id=7)
        assert [(a.id, a.title) for a in repository.list().items] == [(7, 'a')]

    def test_duplicate_key_race_commits_by_default(self, repository, db_engine):
        with concurrent_insert_before_flush(repository, db_engine, id=7, title='other'), \
                mock.patch.object(repository.session, 'commit', wraps=repository.session.commit) as commit:
            repository.update_or_create(update_data={'title': 'a'}, id=7)
        assert commit.call_count == 1

    def test_other_integrity_error_is_translated_to_conflict(self, repository):
        repository.create(data={'title': 'taken'})
        with pytest.raises(exceptions.Conflict):
            repository.update_or_create(update_data={'title': 'taken'}, id=7)
        assert len(repository.list().items) == 1
        assert repository.update_or_create(update_data={'title': 'free'}, id=7).title == 'free'
