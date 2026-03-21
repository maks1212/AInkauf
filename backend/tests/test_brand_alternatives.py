from app.algorithm import suggest_brand_alternatives
from app.schemas import ShoppingListItemInput, StoreProductOffer


def test_brand_alternative_suggestion_with_savings():
    result = suggest_brand_alternatives(
        shopping_list=[
            ShoppingListItemInput(
                name="Milch",
                quantity=2,
                unit="l",
                preferred_brand="MarkeX",
                category="Molkerei",
            )
        ],
        offers=[
            StoreProductOffer(
                store_id="s1",
                chain="Spar",
                product_name="Milch 1L",
                brand="MarkeX",
                category="Molkerei",
                unit="l",
                price_eur=1.8,
                is_brand_product=True,
            ),
            StoreProductOffer(
                store_id="h1",
                chain="Hofer",
                product_name="Milch 1L",
                brand="Eigenmarke",
                category="Molkerei",
                unit="l",
                price_eur=1.2,
            ),
        ],
    )
    assert len(result.suggestions) == 1
    assert result.total_potential_savings_eur == 1.2


def test_brand_alternative_no_suggestion_when_not_cheaper():
    result = suggest_brand_alternatives(
        shopping_list=[
            ShoppingListItemInput(
                name="Pasta",
                quantity=1,
                unit="pack",
                preferred_brand="Premium",
                category="Teigwaren",
            )
        ],
        offers=[
            StoreProductOffer(
                store_id="s1",
                chain="Spar",
                product_name="Pasta Premium",
                brand="Premium",
                category="Teigwaren",
                unit="pack",
                price_eur=1.0,
                is_brand_product=True,
            ),
            StoreProductOffer(
                store_id="h1",
                chain="Hofer",
                product_name="Pasta Basic",
                brand="Basic",
                category="Teigwaren",
                unit="pack",
                price_eur=1.3,
            ),
        ],
    )
    assert len(result.suggestions) == 0
    assert result.total_potential_savings_eur == 0
