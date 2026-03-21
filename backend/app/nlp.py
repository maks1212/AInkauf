import re

from .schemas import ParseResponse

_INPUT_RE = re.compile(
    r"^\s*(?P<quantity>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|l|ml|stk|stück|pack|paket)\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def parse_free_text_item(text: str) -> ParseResponse:
    match = _INPUT_RE.match(text)
    if not match:
        raise ValueError(
            "Konnte Eingabe nicht parsen. Beispiel: '3kg Äpfel' oder '2 l Milch'."
        )

    quantity_raw = match.group("quantity").replace(",", ".")
    unit = match.group("unit").lower()
    if unit == "stück":
        unit = "stk"

    return ParseResponse(
        quantity=float(quantity_raw),
        unit=unit,
        product_name=match.group("name").strip(),
    )
