from app.nlp import parse_free_text_item


def test_parse_text_item():
    result = parse_free_text_item("3kg Aepfel")
    assert result.quantity == 3
    assert result.unit == "kg"
    assert result.product_name == "Aepfel"
