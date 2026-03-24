from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_export_ready_filters_out_unmatched_offers():
    response = client.get("/admin/scraper/export/ready")
    assert response.status_code == 200
    payload = response.json()
    assert "quality_profile" in payload
    assert payload["count_total_candidates"] >= 0
    # Current dataset has no auto-matched offers yet.
    assert payload["count_ready"] == 0
    assert payload["items"] == []


def test_export_ready_alias_endpoint_behaves_identically():
    response = client.get("/price-platform/export/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["quality_profile"]["requires_canonical_product"] is True
    assert payload["quality_profile"]["promo_requires_valid_to"] is True
