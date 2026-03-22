from datetime import date

from app.providers.austria_price_provider import HeisspreiseLiveProvider


def test_heisspreise_decompress_records():
    payload = {
        "stores": ["billa"],
        "dates": [20260322],
        "n": 1,
        # structure:
        # store_idx, product_id, name, category, unavailable,
        # price_history_len, date_idx, amount,
        # unit, quantity, is_weighted, is_bio, url
        "data": [
            0,
            "123",
            "Apfel",
            "Obst",
            0,
            1,
            0,
            2.49,
            "kg",
            1,
            0,
            0,
            "/produkt/apfel",
        ],
    }
    records = HeisspreiseLiveProvider._decompress_records(payload, query_day=date(2026, 3, 22))
    assert len(records) == 1
    assert records[0].store_id == "billa"
    assert records[0].product_key == "apfel_kg"
    assert records[0].price_eur == 2.49
    assert records[0].date.isoformat() == "2026-03-22"
