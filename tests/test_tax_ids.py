import pytest

from faturakit.tax_ids import is_valid_tax_id, is_valid_tckn, is_valid_vkn


def test_valid_vkn():
    assert is_valid_vkn("1234567890")


@pytest.mark.parametrize(
    "vkn", ["1234567891", "0000000000", "123456789", "12345678901", "12345abcde", ""]
)
def test_invalid_vkn(vkn):
    assert not is_valid_vkn(vkn)


def test_valid_tckn():
    assert is_valid_tckn("10000000146")


@pytest.mark.parametrize("tckn", ["10000000147", "00000000146", "1000000014", "1000000014a"])
def test_invalid_tckn(tckn):
    assert not is_valid_tckn(tckn)


def test_is_valid_tax_id_dispatches_by_length():
    assert is_valid_tax_id("1234567890")
    assert is_valid_tax_id("10000000146")
    assert not is_valid_tax_id("123")
    assert not is_valid_tax_id(None)
