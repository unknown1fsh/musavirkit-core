"""VKN (vergi kimlik no) ve TCKN (T.C. kimlik no) kontrol hanesi doğrulaması."""

from __future__ import annotations


def is_valid_vkn(vkn: str) -> bool:
    if len(vkn) != 10 or not vkn.isdigit():
        return False
    digits = [int(c) for c in vkn]
    total = 0
    for i in range(9):
        tmp = (digits[i] + 9 - i) % 10
        value = (tmp * 2 ** (9 - i)) % 9
        if tmp != 0 and value == 0:
            value = 9
        total += value
    return (10 - total % 10) % 10 == digits[9]


def is_valid_tckn(tckn: str) -> bool:
    if len(tckn) != 11 or not tckn.isdigit() or tckn[0] == "0":
        return False
    d = [int(c) for c in tckn]
    odd = d[0] + d[2] + d[4] + d[6] + d[8]
    even = d[1] + d[3] + d[5] + d[7]
    if (odd * 7 - even) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def is_valid_tax_id(tax_id: str | None) -> bool:
    if not tax_id:
        return False
    if len(tax_id) == 10:
        return is_valid_vkn(tax_id)
    if len(tax_id) == 11:
        return is_valid_tckn(tax_id)
    return False
