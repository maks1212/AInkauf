from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_price_platform_chains_returns_tiered_catalog():
    response = client.get("/price-platform/chains")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert any(item["code"] == "billa" for item in payload["items"])
    assert any(item["code"] == "spar" for item in payload["items"])


def test_price_platform_stores_requires_lat_lng_together():
    response = client.get("/price-platform/stores", params={"lat": 48.2})
    assert response.status_code == 422
    assert "lat and lng" in response.json()["detail"]


def test_price_platform_current_price_returns_validity_window():
    response = client.get(
        "/price-platform/prices/current",
        params={
            "store_id": "store-billa-1010",
            "product_key": "gouda",
        },
    )
    assert response.status_code == 200
    payload = response.json()["item"]
    assert payload["store_id"] == "store-billa-1010"
    assert payload["product_key"] == "gouda"
    assert payload["valid_from"] is not None


def test_price_platform_history_includes_multiple_versions():
    response = client.get(
        "/price-platform/prices/history",
        params={
            "store_id": "store-billa-1010",
            "product_key": "pizza_margherita",
        },
    )
    assert response.status_code == 200
    payload = response.json()["items"]
    assert len(payload) >= 2
    assert any(entry["price_type"] == "promo" for entry in payload)


def test_price_platform_promotions_current_returns_active_promos():
    response = client.get("/price-platform/promotions/current")
    assert response.status_code == 200
    payload = response.json()["items"]
    assert payload
    assert all(entry["price_type"] == "promo" for entry in payload)


def test_price_platform_basket_quote_returns_store_quotes():
    response = client.post(
        "/price-platform/basket/quote",
        json={
            "items": [
                {"product_key": "gouda", "quantity": 500, "unit": "g"},
                {"product_key": "milch_1l", "quantity": 1, "unit": "l"},
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()["quotes"]
    assert payload
    assert all("store_id" in store for store in payload)
    assert all(len(store["line_items"]) == 2 for store in payload)
