import pytest
from httpx import AsyncClient
from backend.app import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get('/health')
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_login_and_protected_create_turma():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post('/login', data={'username':'admin','password':'adminpass'})
        assert r.status_code == 200
        token = r.json().get('access_token')
        assert token
        headers = {'Authorization': f'Bearer {token}'}
        # create turma
        r2 = await ac.post('/turmas', json={'nome':'TC Test','capacidade':10}, headers=headers)
        assert r2.status_code == 200 or r2.status_code == 201

@pytest.mark.asyncio
async def test_export_alunos_json():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get('/export/alunos?format=json')
        assert r.status_code == 200
        assert isinstance(r.json(), list)
