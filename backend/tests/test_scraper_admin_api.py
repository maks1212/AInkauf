from datetime import date

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_scraper_admin_catalog_crud_and_serial_uniqueness():
    create_response = client.post(
        "/admin/scraper/catalog",
        json={
            "name": "Gouda 250g",
            "brand": "Clever",
            "serial_number": "9012345678901",
            "package_quantity": 250,
            "package_unit": "g",
            "category": "kaese",
        },
    )
    assert create_response.status_code == 200
    item = create_response.json()["item"]
    product_id = item["id"]

    duplicate = client.post(
        "/admin/scraper/catalog",
        json={
            "name": "Gouda 250g Duplicate",
            "serial_number": "9012345678901",
        },
    )
    assert duplicate.status_code == 400

    patch = client.patch(
        f"/admin/scraper/catalog/{product_id}",
        json={"brand": "S-Budget"},
    )
    assert patch.status_code == 200
    assert patch.json()["item"]["brand"] == "S-Budget"

    delete = client.delete(f"/admin/scraper/catalog/{product_id}")
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True


def test_scraper_admin_job_start_and_offer_review_resolution():
    catalog_create = client.post(
        "/admin/scraper/catalog",
        json={
            "name": "Gouda",
            "brand": "Clever",
            "serial_number": "9010000000001",
            "package_quantity": 250,
            "package_unit": "g",
            "category": "kaese",
        },
    )
    assert catalog_create.status_code == 200
    canonical_id = catalog_create.json()["item"]["id"]

    start_response = client.post(
        "/admin/scraper/jobs/start",
        json={"stores": ["billa", "spar"], "simulate": True},
    )
    assert start_response.status_code == 200
    job_id = start_response.json()["job"]["id"]

    # Wait briefly for async simulated job completion.
    final_jobs = None
    for _ in range(30):
        jobs_response = client.get("/admin/scraper/jobs")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()["items"]
        current = next((row for row in jobs if row["id"] == job_id), None)
        if current and current["status"] in {"success", "failed"}:
            final_jobs = current
            break
    assert final_jobs is not None
    assert final_jobs["status"] == "success"

    offers_response = client.get("/admin/scraper/offers", params={"needs_review": True})
    assert offers_response.status_code == 200
    offers = offers_response.json()["items"]
    assert offers
    first_offer_id = offers[0]["id"]

    reviews_response = client.get("/admin/scraper/reviews")
    assert reviews_response.status_code == 200
    reviews = reviews_response.json()["items"]
    assert reviews
    review_id = reviews[0]["id"]

    resolve_response = client.post(
        f"/admin/scraper/reviews/{review_id}/resolve",
        json={
            "canonical_product_id": canonical_id,
            "reviewer_note": "Matched manually in test",
        },
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["item"]["status"] == "resolved"

    patched_offer = client.patch(
        f"/admin/scraper/offers/{first_offer_id}",
        json={
            "price_eur": 1.99,
            "valid_from": date.today().isoformat(),
            "price_type": "promo",
            "promotion_type": "percent",
            "promotion_label": "-20%",
        },
    )
    assert patched_offer.status_code == 200
    assert patched_offer.json()["item"]["price_type"] == "promo"


def test_scraper_admin_config_validation_and_recommendation():
    get_config = client.get("/admin/scraper/config")
    assert get_config.status_code == 200
    payload = get_config.json()
    assert "config" in payload
    assert "schedule_recommendation" in payload

    update = client.patch(
        "/admin/scraper/config",
        json={
            "enabled": True,
            "interval_minutes": 45,
            "max_parallel_stores": 5,
            "retries": 2,
        },
    )
    assert update.status_code == 200
    config = update.json()["config"]
    assert config["enabled"] is True
    assert config["interval_minutes"] == 45
    assert config["max_parallel_stores"] == 5
    assert config["retries"] == 2
