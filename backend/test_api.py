from fastapi.testclient import TestClient
from backend.main import app

# API'mizi test etmek için sahte bir istemci (tarayıcı) oluşturuyoruz
client = TestClient(app)

def test_var_endpoint():
    # /api/var adresine SPY hissesi için istek atıyoruz
    response = client.get("/api/var?ticker=SPY")
    #1.
    assert response.status_code == 200
    #2. 
    data = response.json()
    assert data["ticker"] == "SPY"