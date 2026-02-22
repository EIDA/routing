from fastapi.testclient import TestClient
from routing import routingws

client = TestClient(routingws)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert '<html>' in response.text.lower()

def test_endpoints():
    response = client.get("/endpoints")
    assert response.status_code == 200
    assert 'http://mydomain.dom/eidaws/routing/1' in response.text

def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.text.startswith('1.3')

def test_info():
    response = client.get("/info")
    assert response.status_code == 200
    assert 'eida' in response.text.lower()

def test_wadl():
    response = client.get("/application.wadl")
    assert response.status_code == 200
    assert '<application ' in response.text.lower()
    assert 'path="globalconfig"' in response.text.lower()
    assert 'path="version"' in response.text.lower()
    assert 'path="query"' in response.text.lower()
    assert 'path="localconfig"' in response.text.lower()

def test_localconfig():
    response = client.get("/localconfig")
    assert response.status_code == 200
    assert 'ns0:route networkCode="4C"' in response.text
    assert 'ns0:route networkCode="GE"' in response.text
    assert 'ns0:route networkCode="CH"' in response.text
    assert 'ns0:route networkCode="RO"' in response.text
    assert 'ns0:route networkCode="ZE"' in response.text

def test_virtualnets():
    response = client.get("/virtualnets")
    assert response.status_code == 200
    assert "_GEALL" in response.json()

def test_globalconfig():
    response = client.get("/globalconfig?format=fdsn")
    assert response.status_code == 200
    assert "version" in response.json()
    assert "datacenters" in response.json()

def test_dc():
    response = client.get("/dc")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "website" in response.json()
    assert "fullName" in response.json()
    assert "summary" in response.json()
    assert "repositories" in response.json()
