"""Rule behaviour tests on small, self-contained fixtures."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from shieldlint.engine import Config, run

from .fixtures import (
    MEMO_LONG,
    SAPLING,
    SECRET,
    SPROUT,
    TADDR,
    TADDR_BAD,
    UA_SHIELDED,
    UA_TESTNET,
    UA_WITH_TRANSPARENT,
    UFVK,
    URI_BAD_AMOUNT,
    URI_MEMO_ON_TADDR,
    URI_SHIELDED,
    URI_TRANSPARENT,
)


class RuleTestCase(unittest.TestCase):
    def lint(self, code: str, *, name: str = "app.py", config: Config | None = None) -> set[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(code), encoding="utf-8")
            report = run([tmp], config or Config(), root=Path(tmp))
            return {finding.rule.id for finding in report.findings}

    def assertFlags(self, code: str, rule: str, **kwargs) -> None:
        found = self.lint(code, **kwargs)
        self.assertIn(rule, found, f"expected {rule}, got {sorted(found)}")

    def assertClean(self, code: str, **kwargs) -> None:
        found = self.lint(code, **kwargs)
        self.assertEqual(found, set(), f"unexpected findings {sorted(found)}")


class TransparentRules(RuleTestCase):
    def test_literal_without_send_context_is_a_warning(self) -> None:
        found = self.lint(f'REFUND = "{TADDR}"\n')
        self.assertIn("SL002", found)
        self.assertNotIn("SL001", found)

    def test_inline_send_to_transparent(self) -> None:
        self.assertFlags(
            f"""
            def pay(wallet):
                wallet.send_payment(recipient="{TADDR}", amount=1)
            """,
            "SL001",
        )

    def test_constant_send_to_transparent(self) -> None:
        self.assertFlags(
            f"""
            REFUND = "{TADDR}"

            def pay(wallet, amount):
                wallet.send_payment(recipient=REFUND, amount=amount)
            """,
            "SL001",
        )

    def test_memo_and_transparent_recipient(self) -> None:
        self.assertFlags(
            f"""
            REFUND = "{TADDR}"

            def pay(wallet):
                wallet.send_payment(recipient=REFUND, memo="order 12")
            """,
            "SL004",
        )

    def test_memo_to_shielded_is_clean(self) -> None:
        self.assertClean(
            f"""
            def pay(wallet):
                wallet.send_payment(recipient="{UA_SHIELDED}", memo="order 12")
            """
        )

    def test_transparent_source(self) -> None:
        self.assertFlags("source = Source::Transparent\n", "SL008")

    def test_ua_with_transparent_receiver(self) -> None:
        self.assertFlags(f'UA = "{UA_WITH_TRANSPARENT}"\n', "SL003")

    def test_malformed_address(self) -> None:
        self.assertFlags(f'ADDR = "{TADDR_BAD}"\n', "SL014")

    def test_sapling_address_is_clean(self) -> None:
        self.assertClean(f'ADDR = "{SAPLING}"\n')


class KeyAndMemoRules(RuleTestCase):
    def test_viewing_key_literal(self) -> None:
        self.assertFlags(f'VIEW_KEY = "{UFVK}"\n', "SL006")

    def test_viewing_key_in_log(self) -> None:
        self.assertFlags(
            """
            def watch(fvk):
                logger.info("watching with %s", fvk)
            """,
            "SL006",
        )

    def test_viewing_key_in_fstring_log(self) -> None:
        self.assertFlags(
            """
            def watch(ufvk):
                print(f"watching {ufvk}")
            """,
            "SL006",
        )

    def test_spending_key_literal(self) -> None:
        self.assertFlags(f'SECRET = "{SECRET}"\n', "SL007")

    def test_spending_key_assignment(self) -> None:
        self.assertFlags('spending_key = "0f" * 32\n', "SL007")

    def test_memo_logged(self) -> None:
        self.assertFlags(
            """
            def settle(order):
                logger.info("memo=%s", order.memo)
            """,
            "SL005",
        )

    def test_memo_hash_logged_is_clean(self) -> None:
        self.assertClean(
            """
            import hashlib

            def settle(order):
                memo_hash = hashlib.sha256(order.memo.encode()).hexdigest()
                logger.info("memo_ref=%s", memo_hash)
            """
        )

    def test_memo_too_long(self) -> None:
        self.assertFlags(f'MEMO_NOTE = "{MEMO_LONG}"\n', "SL012")


class AddressRules(RuleTestCase):
    def test_testnet_address(self) -> None:
        self.assertFlags(f'ADDR = "{UA_TESTNET}"\n', "SL009")

    def test_sprout_address(self) -> None:
        self.assertFlags(f'ADDR = "{SPROUT}"\n', "SL013")

    def test_shielded_ua_is_clean(self) -> None:
        self.assertClean(f'ADDR = "{UA_SHIELDED}"\n')


class UriRules(RuleTestCase):
    def test_transparent_payment_uri(self) -> None:
        self.assertFlags(f'URI = "{URI_TRANSPARENT}"\n', "SL010")

    def test_invalid_payment_uri(self) -> None:
        found = self.lint(f'URI = "{URI_MEMO_ON_TADDR}"\n')
        self.assertIn("SL011", found)

    def test_bad_amount_uri(self) -> None:
        found = self.lint(f'URI = "{URI_BAD_AMOUNT}"\n')
        self.assertIn("SL011", found)

    def test_shielded_uri_is_clean(self) -> None:
        self.assertClean(f'URI = "{URI_SHIELDED}"\n')

    def test_dynamic_uri_is_not_parsed(self) -> None:
        self.assertClean(
            f"""
            def uri(u):
                return f"zcash:{{u}}?amount=1"
            """
        )


class SuppressionAndConfig(RuleTestCase):
    def test_inline_ignore(self) -> None:
        self.assertClean(f'ADDR = "{TADDR}"  # shieldlint: ignore[SL002]\n')

    def test_ignore_whole_rule_set(self) -> None:
        self.assertClean(f'ADDR = "{TADDR}"  # shieldlint: ignore\n')

    def test_disable_file(self) -> None:
        self.assertClean(
            f'# shieldlint: disable-file\nADDR = "{TADDR}"\n'
        )

    def test_config_disable(self) -> None:
        config = Config(disable={"SL002"})
        self.assertClean(f'ADDR = "{TADDR}"\n', config=config)

    def test_config_severity_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.py"
            path.write_text(f'ADDR = "{TADDR}"\n', encoding="utf-8")
            config = Config(severity={"SL002": "error"})
            report = run([tmp], config, root=Path(tmp))
            self.assertEqual(report.errors, 1)
            self.assertEqual(report.warnings, 0)

    def test_fail_on_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.py"
            path.write_text(f'ADDR = "{TADDR}"\n', encoding="utf-8")
            config = Config(fail_on="warning")
            report = run([tmp], config, root=Path(tmp))
            self.assertTrue(report.exceeds_threshold())
            self.assertFalse(run([tmp], Config(fail_on="never"), root=Path(tmp)).exceeds_threshold())


class LanguageCoverage(RuleTestCase):
    def test_javascript_template_and_comments(self) -> None:
        found = self.lint(
            """
            // refund address: "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY" (comment, ignored)
            const addr = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY";
            """,
            name="wallet.ts",
        )
        # exactly one finding: the literal, not the commented-out one
        self.assertEqual(found, {"SL002"})

    def test_javascript_regex_with_quotes(self) -> None:
        found = self.lint(
            """
            const quote = /["'`]/g;                 // regex literal, not a string
            const addr = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY";
            """,
            name="wallet.js",
        )
        self.assertEqual(found, {"SL002"})

    def test_rust_char_literal_with_quote(self) -> None:
        found = self.lint(
            """
            pub const Q: char = '"';
            pub const UA: &str = "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9xh6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lkw6uh7hyvzjse8ksx";
            """,
            name="wallet.rs",
        )
        self.assertEqual(found, {"SL003"})

    def test_rust_suppression(self) -> None:
        found = self.lint(
            """
            // shieldlint: ignore[SL003]
            const UA: &str = "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9xh6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lkw6uh7hyvzjse8ksx";
            """,
            name="wallet.rs",
        )
        self.assertNotIn("SL003", found)


if __name__ == "__main__":
    unittest.main()
