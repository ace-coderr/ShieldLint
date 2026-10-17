"""ZIP 321 conformance tests, including the examples in the ZIP itself."""

from __future__ import annotations

import unittest

from shieldlint.uri import parse_payment_uri
from tests.fixtures import (
    TADDR,
    UA_SHIELDED,
    URI_MEMO_ON_TADDR,
    URI_SHIELDED,
    URI_TRANSPARENT,
)

ZIP_EXAMPLE_1 = (
    "zcash:ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez"
    "?amount=1&memo=VGhpcyBpcyBhIHNpbXBsZSBtZW1vLg&message=Thank%20you%20for%20your%20purchase"
)
ZIP_EXAMPLE_2 = (
    "zcash:?address=tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU&amount=123.456"
    "&address.1=ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez"
    "&amount.1=0.789&memo.1=VGhpcyBpcyBhIHVuaWNvZGUgbWVtbyDinKjwn6aE8J-PhvCfjok"
)
INVALID_EXAMPLES = [
    # missing address for the unindexed parameters
    "zcash:?amount=3491405.05201255&address.1=ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez&amount.1=5740296.87793245",
    # amount.1 has no address.1
    "zcash:?address=tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU&amount=1&amount.1=2&address.2=ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez",
    # leading zero in paramindex
    "zcash:?address.0=ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez&amount.0=2",
    # duplicate amount
    "zcash:?amount=1.234&amount=2.345&address=tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU",
    # percent-encoding outside qchar productions
    "zcash:tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU?amount=1%30",
    "zcash:tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU?%61mount=1",
    "zcash:%74mEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU?amount=1",
    # authority not allowed
    "zcash://tmEZhbWHTpdKMw5it8YDspUXSMGQyFwovpU?amount=1",
    # req-asset with a Sapling address, plus invalid base64url
    "zcash:?address=ztestsapling10yy2ex5dcqkclhc7z7yrnjq2z6feyjad56ptwlfgmy77dmaqqrl9gyhprdx59qgmsnyfska2kez&amount=5&req-asset=not@valid!chars",
]


class ValidRequests(unittest.TestCase):
    def test_zip_examples(self) -> None:
        first = parse_payment_uri(ZIP_EXAMPLE_1)
        self.assertTrue(first.ok, first.errors)
        self.assertEqual(len(first.payments), 1)
        self.assertEqual(first.payments[0].amount, 1)
        self.assertEqual(first.payments[0].memo[:5], b"This ")

        second = parse_payment_uri(ZIP_EXAMPLE_2)
        self.assertTrue(second.ok, second.errors)
        self.assertEqual([p.index for p in second.payments], ["", "1"])
        from decimal import Decimal

        self.assertEqual(second.payments[1].amount, Decimal("0.789"))

    def test_shielded_request(self) -> None:
        request = parse_payment_uri(URI_SHIELDED)
        self.assertTrue(request.ok, request.errors)
        self.assertFalse(request.payments[0].is_transparent)

    def test_transparent_request_is_valid_but_flagged(self) -> None:
        request = parse_payment_uri(URI_TRANSPARENT)
        self.assertTrue(request.ok, request.errors)
        self.assertEqual(len(request.transparent_payments), 1)

    def test_amount_formatting(self) -> None:
        for value in ("50", "050", "0.5", "00.500", "50.00"):
            request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount={value}")
            self.assertTrue(request.ok, (value, request.errors))

    def test_unknown_optional_parameter_is_ignored(self) -> None:
        request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount=1&campaign=shop")
        self.assertTrue(request.ok, request.errors)
        self.assertTrue(request.warnings)


class InvalidRequests(unittest.TestCase):
    def test_zip_invalid_examples(self) -> None:
        for raw in INVALID_EXAMPLES:
            request = parse_payment_uri(raw)
            self.assertFalse(request.ok, f"accepted invalid URI: {raw}")

    def test_memo_on_transparent(self) -> None:
        request = parse_payment_uri(URI_MEMO_ON_TADDR)
        self.assertFalse(request.ok)
        self.assertIn("transparent", " ".join(request.errors))

    def test_memo_too_long(self) -> None:
        import base64

        memo = base64.urlsafe_b64encode(b"x" * 513).decode().rstrip("=")
        request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount=1&memo={memo}")
        self.assertFalse(request.ok)

    def test_memo_padding_rejected(self) -> None:
        request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount=1&memo=b3JkZXI6MQ==")
        self.assertFalse(request.ok)

    def test_amount_limits(self) -> None:
        for value in ("50.", ".5", "0.123456789", "50,000.00", "21000001"):
            request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount={value}")
            self.assertFalse(request.ok, value)

    def test_duplicate_parameter(self) -> None:
        request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount=1&memo=a&memo=b")
        self.assertFalse(request.ok)

    def test_unknown_required_parameter(self) -> None:
        request = parse_payment_uri(f"zcash:{UA_SHIELDED}?amount=1&req-unknown=1")
        self.assertFalse(request.ok)

    def test_sprout_is_rejected(self) -> None:
        sprout = "zc8E7R3StiJq1T1UaCdygazuEVBe9xddGdYBLMe8WNgnBTVRGiGwY9MEeVKqhWNtmbPmwi4S1uJtPobqCq4azuLJrKCFjcj"
        request = parse_payment_uri(f"zcash:{sprout}?amount=1")
        self.assertFalse(request.ok)


if __name__ == "__main__":
    unittest.main()
