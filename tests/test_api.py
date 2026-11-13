"""Live integration tests. Opt in explicitly; only test-created records are deleted."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(os.getenv('RUN_MONGODB_TESTS') != '1', reason='Set RUN_MONGODB_TESTS=1 to use the configured MongoDB database.')


@pytest.fixture(scope='module')
def client():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client


def test_full_crud_and_persistence(client):
    payload = {'title': f'CRUD verification {uuid4().hex}', 'notes': 'Temporary integration-test record.', 'priority': 'high', 'status': 'todo'}
    created = client.post('/api/tasks', json=payload)
    assert created.status_code == 201
    task = created.json()
    task_id = task['id']
    try:
        # Fresh queries verify the saved document, rather than a client-side cache.
        assert client.get(f'/api/tasks/{task_id}').json()['title'] == payload['title']
        assert task_id in {row['id'] for row in client.get('/api/tasks').json()}
        update = {**payload, 'title': payload['title'] + ' updated', 'status': 'done'}
        result = client.put(f'/api/tasks/{task_id}', json=update)
        assert result.status_code == 200
        reread = client.get(f'/api/tasks/{task_id}').json()
        assert reread['status'] == 'done'
        assert reread['title'] == update['title']
        assert reread['created_at'] == task['created_at']
        assert reread['updated_at'] >= task['updated_at']
        assert client.delete(f'/api/tasks/{task_id}').status_code == 204
        assert client.get(f'/api/tasks/{task_id}').status_code == 404
        assert client.delete(f'/api/tasks/{task_id}').status_code == 404
    finally:
        client.delete(f'/api/tasks/{task_id}')


@pytest.mark.parametrize('payload', [
    {'title': '   '}, {'title': 'x' * 121}, {'title': 'Valid', 'status': 'invalid'},
    {'title': 'Valid', 'priority': 'invalid'}, {'title': 'Valid', 'notes': 'x' * 2001},
    {'title': 'Valid', 'unexpected': 'field'},
])
def test_validation(client, payload):
    assert client.post('/api/tasks', json=payload).status_code == 422


def test_missing_and_invalid_ids(client):
    assert client.get('/api/tasks/not-an-id').status_code == 422
    assert client.get('/api/tasks/000000000000000000000000').status_code == 404


def test_cross_origin_writes_are_rejected(client):
    response = client.post('/api/tasks', json={'title': 'Should not save'}, headers={'Origin': 'https://untrusted.example'})
    assert response.status_code == 403


def test_health_ui_and_secret_boundary(client):
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['status'] == 'connected'
    assert set(health.json()) == {'status', 'database', 'collection'}
    page = client.get('/')
    assert page.status_code == 200
    assert 'Little Wins' in page.text
    assert 'mongodb+srv://' not in page.text
    assert client.get('/.env').status_code == 404
    assert client.get('/static/app.js').status_code == 200
