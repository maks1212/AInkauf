from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_scraper_event_history_contains_auto_and_manual_decisions():
    client.post("/admin/scraper/reset")
    catalog = client.post(
        "/admin/scraper/catalog",
        json={
            "name": "Gouda",
            "brand": "Clever",
            "serial_number": "9010000099999",
            "package_quantity": 250,
            "package_unit": "g",
            "category": "kaese",
        },
    )
    assert catalog.status_code == 200
    canonical_id = catalog.json()["item"]["id"]

    start = client.post(
        "/admin/scraper/jobs/start",
        json={"stores": ["billa"], "simulate": True},
    )
    assert start.status_code == 200
    job_id = start.json()["job"]["id"]

    # wait for completion
    for _ in range(40):
        jobs = client.get("/admin/scraper/jobs")
        assert jobs.status_code == 200
        current = next((row for row in jobs.json()["items"] if row["id"] == job_id), None)
        if current and current["status"] in {"success", "failed"}:
            break

    events = client.get("/admin/scraper/events")
    assert events.status_code == 200
    items = events.json()["items"]
    assert any(event["event_type"] == "MATCHED_AUTO" for event in items)
    assert any(event["event_type"] in {"NEW_LISTING", "PRICE_CHANGE_UP", "PRICE_CHANGE_DOWN", "NO_MATERIAL_CHANGE"} for event in items)

    reviews = client.get("/admin/scraper/reviews")
    assert reviews.status_code == 200
    pending = reviews.json()["items"]
    if pending:
        review_id = pending[0]["id"]
        resolve = client.post(
            f"/admin/scraper/reviews/{review_id}/resolve",
            json={
                "canonical_product_id": canonical_id,
                "reviewer_note": "manual confirm",
            },
        )
        assert resolve.status_code == 200
        review_events = client.get("/admin/scraper/events", params={"actor_type": "reviewer"})
        assert review_events.status_code == 200
        assert any(event["event_type"] == "REVIEW_RESOLVED" for event in review_events.json()["items"])
