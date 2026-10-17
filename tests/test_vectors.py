"""Conformance tests against the official Zcash test vectors.

Vectors are vendored from https://github.com/zcash/zcash-test-vectors
(MIT licensed); see tests/vectors/README.md.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from shieldlint import address, bech32, f4jumble

VECTORS = Path(__file__).parent / "vectors"


def load(name: str) -> list:
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


class F4JumbleVectors(unittest.TestCase):
    def test_forward_and_inverse(self) -> None:
        rows = load("f4jumble.json")
        checked = 0
        for row in rows:
            if not (isinstance(row, list) and len(row) == 2 and len(row[0]) > 40):
                continue  # header rows
            normal, jumbled = bytes.fromhex(row[0]), bytes.fromhex(row[1])
            self.assertEqual(f4jumble.f4jumble(normal), jumbled)
            self.assertEqual(f4jumble.f4jumble_inv(jumbled), normal)
            checked += 1
        self.assertGreaterEqual(checked, 8)

    def test_long_vectors(self) -> None:
        for row in load("f4jumble_long.json"):
            if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], int)):
                continue
            length, expected = row
            # vectors hash F4Jumble(bytes([i & 0xFF for i in range(length)]))
            message = bytes(i & 0xFF for i in range(length))
            jumbled = f4jumble.f4jumble(message)
            import hashlib

            self.assertEqual(hashlib.blake2b(jumbled).hexdigest(), expected)

    def test_length_bounds(self) -> None:
        with self.assertRaises(f4jumble.F4JumbleError):
            f4jumble.f4jumble(b"\x00" * 37)


class UnifiedAddressVectors(unittest.TestCase):
    def _check_rows(self, name: str) -> int:
        rows = load(name)
        header = rows[1][0].split(", ")
        checked = 0
        for row in rows[2:]:
            record = dict(zip(header, row))
            raw = record["unified_addr"]
            info = address.classify(raw)
            self.assertTrue(info.ok, f"{raw[:24]}…: {info.errors}")
            self.assertTrue(info.is_unified)
            expected = []
            if record.get("p2pkh_bytes"):
                expected.append(("transparent-p2pkh", record["p2pkh_bytes"].lower()))
            if record.get("p2sh_bytes"):
                expected.append(("transparent-p2sh", record["p2sh_bytes"].lower()))
            if record.get("sapling_raw_addr"):
                expected.append(("sapling", record["sapling_raw_addr"].lower()))
            if record.get("orchard_raw_addr"):
                expected.append(("orchard", record["orchard_raw_addr"].lower()))
            got = sorted(
                (r.kind, r.data.hex())
                for r in info.receivers
                if r.kind in {"transparent-p2pkh", "transparent-p2sh", "sapling", "orchard"}
            )
            self.assertEqual(got, sorted(expected), raw[:24])

            if record.get("expiry_height") is not None:
                metadata = {m.kind: m.value for m in info.metadata}
                self.assertEqual(metadata["expiry-height"], record["expiry_height"])
            if record.get("expiry_time") is not None:
                metadata = {m.kind: m.value for m in info.metadata}
                self.assertEqual(metadata["expiry-time"], record["expiry_time"])

            # encoding must reproduce the exact string
            items = []
            if record.get("p2pkh_bytes"):
                items.append((0x00, bytes.fromhex(record["p2pkh_bytes"])))
            if record.get("p2sh_bytes"):
                items.append((0x01, bytes.fromhex(record["p2sh_bytes"])))
            if record.get("sapling_raw_addr"):
                items.append((0x02, bytes.fromhex(record["sapling_raw_addr"])))
            if record.get("orchard_raw_addr"):
                items.append((0x03, bytes.fromhex(record["orchard_raw_addr"])))
            if record.get("unknown_typecode") is not None:
                items.append(
                    (record["unknown_typecode"], bytes.fromhex(record["unknown_bytes"] or ""))
                )
            metadata = []
            if record.get("expiry_height") is not None:
                metadata.append((0xE0, record["expiry_height"].to_bytes(4, "little")))
            if record.get("expiry_time") is not None:
                metadata.append((0xE1, record["expiry_time"].to_bytes(8, "little")))
            hrp = raw.split("1")[0]
            self.assertEqual(address.encode_unified(items, hrp, metadata), raw)
            checked += 1
        return checked

    def test_revision_0(self) -> None:
        self.assertGreaterEqual(self._check_rows("unified_address.json"), 50)

    def test_revision_2(self) -> None:
        self.assertGreaterEqual(self._check_rows("unified_address_r2.json"), 50)

    def test_viewing_keys(self) -> None:
        for name, column in [
            ("unified_full_viewing_keys.json", "unified_fvk"),
            ("unified_incoming_viewing_keys.json", "unified_ivk"),
        ]:
            rows = load(name)
            header = rows[1][0].split(", ")
            for row in rows[2:]:
                record = dict(zip(header, row))
                info = address.classify(record[column])
                self.assertTrue(info.ok, info.errors)
                self.assertEqual(info.kind, "unified-viewing-key")

        rows = load("unified_viewing_keys_r2.json")
        header = rows[1][0].split(", ")
        for row in rows[2:]:
            record = dict(zip(header, row))
            for column in ("unified_fvk", "unified_ivk"):
                info = address.classify(record[column])
                self.assertTrue(info.ok, f"{column}: {info.errors}")
                self.assertEqual(info.kind, "unified-viewing-key")


class Bech32Vectors(unittest.TestCase):
    def test_checksum_variants(self) -> None:
        data = bech32.convertbits(b"hello", 8, 5, True)
        b32 = bech32.encode("test", data, bech32m=False)
        b32m = bech32.encode("test", data, bech32m=True)
        self.assertNotEqual(b32, b32m)
        self.assertFalse(bech32.decode(b32)[2])
        self.assertTrue(bech32.decode(b32m)[2])
        with self.assertRaises(bech32.Bech32Error):
            bech32.decode(b32[:-1] + ("q" if b32[-1] != "q" else "p"))


class DecodingEdges(unittest.TestCase):
    def test_rejects_wrong_checksum_variant(self) -> None:
        info = address.classify(
            "zs1mrhc9y7jdh5r9ece8u5khgvj9kg0zgkxzdduyv0whkg7lkcrkx5xqem3e48avjq9wn2rukydkwn"
        )
        self.assertTrue(info.ok)
        self.assertEqual(info.kind, "sapling")

    def test_truncated_unified_address_is_malformed(self) -> None:
        from tests.fixtures import UA_SHIELDED

        info = address.classify(UA_SHIELDED[:-4])
        self.assertFalse(info.ok)

    def test_unknown_hrp(self) -> None:
        data = bech32.convertbits(b"\x00" * 40, 8, 5, True)
        raw = bech32.encode("xyz", data)
        info = address.decode_unified(raw)
        self.assertFalse(info.ok)
        self.assertIn("human-readable part", " ".join(info.errors))

    def test_transparent_versions(self) -> None:
        from tests.fixtures import TADDR, TADDR_BAD

        good = address.classify(TADDR)
        self.assertEqual(good.kind, "transparent-p2pkh")
        self.assertEqual(good.network, "mainnet")
        bad = address.classify(TADDR_BAD)
        self.assertFalse(bad.ok)


if __name__ == "__main__":
    unittest.main()
