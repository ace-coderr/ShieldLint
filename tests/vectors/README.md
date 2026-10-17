# Vendored Zcash test vectors

These files are copied unmodified from
[`zcash/zcash-test-vectors`](https://github.com/zcash/zcash-test-vectors)
(`test-vectors/json/`), which is MIT licensed:

* `f4jumble.json`, `f4jumble_long.json`
* `unified_address.json`, `unified_address_r2.json`
* `unified_full_viewing_keys.json`, `unified_incoming_viewing_keys.json`,
  `unified_viewing_keys_r2.json`

They are used by `tests/test_vectors.py` to verify that ShieldLint's
implementations of F4Jumble and ZIP 316 match every reference vector,
byte for byte, in both directions. Do not edit them.
