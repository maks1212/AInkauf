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
    assert result.suggestions[0].alternative_type == "no_name"


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


def test_brand_alternative_prefers_chain_budget_brand_for_billa():
    result = suggest_brand_alternatives(
        shopping_list=[
            ShoppingListItemInput(
                name="Nudeln",
                quantity=1,
                unit="pack",
                preferred_brand="Barilla",
                category="Teigwaren",
            )
        ],
        offers=[
            StoreProductOffer(
                store_id="b1",
                chain="Billa",
                product_name="Barilla Nudeln 500g",
                brand="Barilla",
                category="Teigwaren",
                unit="pack",
                price_eur=2.69,
                is_brand_product=True,
            ),
            StoreProductOffer(
                store_id="b2",
                chain="Billa",
                product_name="Clever Nudeln 500g",
                brand="clever",
                category="Teigwaren",
                unit="pack",
                price_eur=1.19,
                is_brand_product=True,
            ),
            StoreProductOffer(
                store_id="h1",
                chain="Hofer",
                product_name="Premium Pasta 500g",
                brand="La Molisana",
                category="Teigwaren",
                unit="pack",
                price_eur=0.99,
                is_brand_product=True,
            ),
        ],
    )
    assert len(result.suggestions) == 1
    suggestion = result.suggestions[0]
    assert suggestion.alternative_brand == "clever"
    assert suggestion.alternative_type == "no_name"
    assert suggestion.chain_budget_reference == "clever"


def test_brand_alternative_normalizes_gram_quantities():
    result = suggest_brand_alternatives(
        shopping_list=[
            ShoppingListItemInput(
                name="Schinken",
                quantity=500,
                unit="g",
                preferred_brand="MarkeX",
                category="Wurst",
            )
        ],
        offers=[
            StoreProductOffer(
                store_id="s1",
                chain="Spar",
                product_name="Schinken MarkeX 500g",
                brand="MarkeX",
                category="Wurst",
                unit="g",
                price_eur=16.0,
                is_brand_product=True,
            ),
            StoreProductOffer(
                store_id="s2",
                chain="Spar",
                product_name="Schinken S-Budget 500g",
                brand="s-budget",
                category="Wurst",
                unit="g",
                price_eur=10.0,
                is_brand_product=True,
            ),
        ],
    )
    assert len(result.suggestions) == 1
    suggestion = result.suggestions[0]
    assert suggestion.preferred_total_eur == 8.0
    assert suggestion.alternative_total_eur == 5.0
    assert suggestion.savings_eur == 3.0
