import pytest

from core.unit_converter import UnitConverter, convert, get_units


@pytest.fixture
def converter():
    return UnitConverter()


def test_pressure_conversion_psi_to_bar(converter):
    result = converter.convert(145.038, "pressure", "psi", "bar")
    assert pytest.approx(10.0, rel=1e-3) == result


def test_flow_rate_conversion_m3s_to_m3h(converter):
    result = converter.convert(1.0, "flow_rate", "m3_per_s", "m3_per_h")
    assert result == pytest.approx(3600.0)


def test_volume_conversion_bbl_to_m3(converter):
    result = converter.convert(10.0, "volume", "bbl", "m3")
    assert pytest.approx(1.58987, rel=1e-5) == result


def test_temperature_round_trip(converter):
    fahrenheit = converter.convert(100.0, "temperature", "celsius", "fahrenheit")
    kelvin = converter.convert(100.0, "temperature", "celsius", "kelvin")
    rankine = converter.convert(100.0, "temperature", "celsius", "rankine")

    assert fahrenheit == pytest.approx(212.0)
    assert kelvin == pytest.approx(373.15)
    assert rankine == pytest.approx(671.67, rel=1e-4)


def test_api_gravity_convert_sg_to_api_and_back(converter):
    api_value = converter.convert(0.8, "api_gravity", "sg", "api")
    sg_value = converter.convert(api_value, "api_gravity", "api", "sg")

    assert api_value == pytest.approx(45.375, rel=1e-3)
    assert sg_value == pytest.approx(0.8, rel=1e-3)


def test_get_units_and_label(converter):
    labels = converter.get_units("power")
    assert labels["hp"] == "HP (mech)"
    assert converter.label("power", "hp") == "HP (mech)"
    assert converter.label("power", "unknown_unit") == "unknown_unit"


def test_get_categories_contains_temperature_and_pressure(converter):
    categories = converter.get_categories()
    assert "temperature" in categories
    assert "pressure" in categories


def test_to_si_and_from_si_round_trip(converter):
    bar_value = converter.to_si(14.5038, "pressure", "psi")
    psi_value = converter.from_si(bar_value, "pressure", "psi")

    assert psi_value == pytest.approx(14.5038, rel=1e-5)


def test_convert_batch_uses_mappings(converter):
    values = {"pressure": 100.0, "flow": 1.0}
    mappings = {
        "pressure": ("pressure", "psi", "bar"),
        "flow": ("flow_rate", "m3_per_s", "m3_per_h"),
    }
    result = converter.convert_batch(values, mappings)

    assert result["pressure"] == pytest.approx(6.89476, rel=1e-6)
    assert result["flow"] == pytest.approx(3600.0)


def test_module_level_shortcuts():
    assert convert(32.0, "temperature", "fahrenheit", "celsius") == pytest.approx(0.0, abs=1e-6)
    assert get_units("temperature")["kelvin"] == "K"


def test_unknown_category_raises_error(converter):
    with pytest.raises(ValueError, match="Unknown unit category"):
        converter.convert(1.0, "unknown_category", "a", "b")


def test_unknown_unit_raises_error(converter):
    with pytest.raises(ValueError, match="Unknown unit 'xyz'"):
        converter.convert(1.0, "pressure", "xyz", "bar")


def test_unknown_temperature_unit_raises_error(converter):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        converter.convert(100.0, "temperature", "bad", "celsius")


def test_unknown_api_gravity_unit_raises_error(converter):
    with pytest.raises(ValueError, match="Unknown API gravity unit"):
        converter.convert(100.0, "api_gravity", "bad", "api")
