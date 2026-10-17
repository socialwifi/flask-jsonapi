import importlib.util
import json
import pathlib

import pytest

EXAMPLE_PATH = pathlib.Path(__file__).parent.parent / 'docs' / 'examples' / 'full_example.py'
JSONAPI = 'application/vnd.api+json'

ARTICLE = {
    'type': 'articles',
    'id': '1',
    'attributes': {'title': 'Hello', 'body': 'First post.'},
    'relationships': {'author': {'data': {'type': 'authors', 'id': '1'}}},
}


def error_document(status, title, detail):
    return {'errors': [{'status': status, 'title': title, 'detail': detail}], 'jsonapi': {'version': '1.0'}}


@pytest.fixture
def client():
    # A fresh module per test means a fresh engine, and with it an empty in-memory database.
    spec = importlib.util.spec_from_file_location('full_example', EXAMPLE_PATH)
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    example.create_database()
    return example.app.test_client()


def send(client, method, url, token=None, body=None):
    headers = {'Accept': JSONAPI}
    if token:
        headers['Authorization'] = 'Bearer {}'.format(token)
    if body is not None:
        headers['Content-Type'] = JSONAPI
    return client.open(url, method=method, headers=headers, data=json.dumps(body) if body is not None else None)


def create_article(client):
    body = {'data': {'type': 'articles', 'attributes': {'title': 'Hello', 'body': 'First post.'}}}
    return send(client, 'POST', '/articles/', token='alice-token', body=body)


def retitle(client, token):
    body = {'data': {'type': 'articles', 'id': '1', 'attributes': {'title': 'Mine now'}}}
    return send(client, 'PATCH', '/articles/1/', token=token, body=body)


def test_request_without_token_is_unauthorized(client):
    response = send(client, 'GET', '/articles/')

    assert response.status_code == 401
    assert response.get_json(force=True) == error_document(401, 'Unauthorized', 'A valid bearer token is required.')


def test_create_makes_the_client_the_author(client):
    response = create_article(client)

    assert response.status_code == 201
    assert response.get_json(force=True) == {'data': ARTICLE, 'jsonapi': {'version': '1.0'}}


def test_any_client_with_a_token_lists_articles(client):
    create_article(client)

    response = send(client, 'GET', '/articles/', token='bob-token')

    assert response.status_code == 200
    assert response.get_json(force=True) == {'data': [ARTICLE], 'meta': {'count': 1}, 'jsonapi': {'version': '1.0'}}


def test_paginated_list_has_links_built_from_the_total(client):
    create_article(client)
    page = 'http://localhost:5000/articles/?page[size]=1&page[number]=1'

    response = client.get(
        '/articles/?page[size]=1&page[number]=1', base_url='http://localhost:5000',
        headers={'Accept': JSONAPI, 'Authorization': 'Bearer bob-token'},
    )

    assert response.status_code == 200
    assert response.get_json(force=True) == {
        'data': [ARTICLE],
        'links': {'self': page, 'first': page, 'previous': None, 'next': None, 'last': page},
        'meta': {'count': 1},
        'jsonapi': {'version': '1.0'},
    }


def test_update_by_someone_else_is_forbidden_and_changes_nothing(client):
    create_article(client)

    response = retitle(client, token='bob-token')

    assert response.status_code == 403
    assert response.get_json(force=True) == error_document(403, 'Forbidden', 'Only the author can change an article.')
    title = send(client, 'GET', '/articles/1/', token='alice-token').get_json(force=True)['data']['attributes']['title']
    assert title == 'Hello'


def test_author_can_update(client):
    create_article(client)

    response = retitle(client, token='alice-token')

    assert response.status_code == 200
    assert response.get_json(force=True)['data']['attributes']['title'] == 'Mine now'


def test_undeclared_delete_is_not_allowed(client):
    create_article(client)

    response = send(client, 'DELETE', '/articles/1/', token='alice-token')

    assert response.status_code == 405
    assert response.get_json(force=True) == error_document(
        405, 'Method not allowed', 'Delete is not allowed for this resource')


def test_author_can_be_included(client):
    create_article(client)

    response = send(client, 'GET', '/articles/1/?include=author', token='bob-token')

    assert response.status_code == 200
    assert response.get_json(force=True)['included'] == [
        {'type': 'authors', 'id': '1', 'attributes': {'name': 'Alice'}},
    ]


def test_client_chosen_id_already_in_use_is_a_conflict(client):
    create_article(client)
    body = {'data': {'type': 'articles', 'id': '1', 'attributes': {'title': 'Taken', 'body': ''}}}

    response = send(client, 'POST', '/articles/', token='alice-token', body=body)

    assert response.status_code == 409
    assert response.get_json(force=True)['errors'][0]['status'] == 409


def test_request_without_accept_header_is_served(client):
    response = client.get('/articles/', headers={'Authorization': 'Bearer bob-token'})

    assert response.status_code == 200


def test_request_accepting_anything_is_not_acceptable(client):
    response = client.get('/articles/', headers={'Authorization': 'Bearer bob-token', 'Accept': '*/*'})

    assert response.status_code == 406
