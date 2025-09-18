from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_login_and_protected_create_turma():
    r = client.post('/login', data={'username':'admin','password':'adminpass'})
    assert r.status_code == 200
    token = r.json().get('access_token')
    assert token
    headers = {'Authorization': f'Bearer {token}'}
    r2 = client.post('/turmas', json={'nome':'TC Test','capacidade':10}, headers=headers)
    assert r2.status_code in (200, 201)

def test_export_alunos_json():
    r = client.get('/export/alunos?format=json')
    assert r.status_code == 200
    assert isinstance(r.json(), list)
