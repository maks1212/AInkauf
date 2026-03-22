import asyncio
import pytest

from app.providers.fuel_provider import EControlFuelProvider


def test_econtrol_provider_rejects_strom():
    provider = EControlFuelProvider()
    with pytest.raises(ValueError, match="keine Strom-Ladepreise"):
        asyncio.run(
            provider.get_cheapest_quote(
                lat=48.2082,
                lng=16.3738,
                fuel_type="strom",
            )
        )
