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

def test_dataselect_get_GE_noformat():
    response = client.get("/query", params={"net": "GE"})
    assert response.status_code == 200
    assert '<url>https://geofon.gfz.de/fdsnws/dataselect/1/query</url>' in response.text
    assert '<net>GE</net>' in response.text
    assert '<priority>1</priority>' in response.text

def test_dataselect_get_GE_xml():
    response = client.get("/query", params={"net": "GE", "format": "xml"})
    assert response.status_code == 200
    assert '<url>https://geofon.gfz.de/fdsnws/dataselect/1/query</url>' in response.text
    assert '<net>GE</net>' in response.text
    assert '<priority>1</priority>' in response.text

def test_dataselect_get_GE_post():
    response = client.get("/query", params={"net": "GE", "format": "post"})
    assert response.status_code == 200
    assert 'https://geofon.gfz.de/fdsnws/dataselect/1/query' in response.text
    assert 'GE * * * 1993-01-01' in response.text

def test_dataselect_get_GE_get():
    response = client.get("/query", params={"net": "GE", "format": "get"})
    assert response.status_code == 200
    assert response.text == 'https://geofon.gfz.de/fdsnws/dataselect/1/query?net=GE&start=1993-01-01T00:00:00'

def test_station_get_GE_noformat():
    response = client.get("/query", params={"net": "GE", "service": "station"})
    assert response.status_code == 200
    assert '<url>https://geofon.gfz.de/fdsnws/station/1/query</url>' in response.text
    assert '<net>GE</net>' in response.text
    assert '<priority>1</priority>' in response.text

def test_station_get_GE_xml():
    response = client.get("/query", params={"net": "GE", "service": "station", "format": "xml"})
    assert response.status_code == 200
    assert '<url>https://geofon.gfz.de/fdsnws/station/1/query</url>' in response.text
    assert '<net>GE</net>' in response.text
    assert '<priority>1</priority>' in response.text

def test_station_get_GE_post():
    response = client.get("/query", params={"net": "GE", "service": "station", "format": "post"})
    assert response.status_code == 200
    assert 'https://geofon.gfz.de/fdsnws/station/1/query' in response.text
    assert 'GE * * * 1993-01-01' in response.text

def test_station_get_GE_get():
    response = client.get("/query", params={"net": "GE", "service": "station", "format": "get"})
    assert response.status_code == 200
    assert response.text == 'https://geofon.gfz.de/fdsnws/station/1/query?net=GE&start=1993-01-01T00:00:00'

def test_dataselect_get_4C_KES27_HNZ_get():
    response = client.get("/query", params={"net": "4C", "sta": "KES27", "cha": "HNZ", "format": "get"})
    assert response.status_code == 200
    assert response.text == 'https://geofon.gfz.de/fdsnws/dataselect/1/query?net=4C&sta=KES27&cha=HNZ&start=2011-09-15T00:00:00&end=2012-04-20T23:59:00'
