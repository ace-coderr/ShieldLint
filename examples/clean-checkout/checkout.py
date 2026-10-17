"""The same merchant checkout, with the privacy bugs fixed.

Everything here is lint-clean: the merchant is paid at a shielded-only
`zu1…` Unified Address, memos never reach logs, and the ZIP 321 request is
static, valid, and points at a shielded recipient.
"""

from __future__ import annotations

import base64
import hashlib
import logging

logger = logging.getLogger("checkout")

# Shielded-only Unified Address (ZIP 316 revision 2, `zu` prefix):
# Orchard + Sapling receivers, no transparent receiver to downgrade to.
SHIELDED_UA = (
    "zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm"
    "5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc0"
    "7fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3"
)

# A valid ZIP 321 request: shielded recipient, amount, and a memo that fits.
CHECKOUT_URI = "zcash:zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc07fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3?amount=0.5&memo=b3JkZXI6T1JELTIyOTE"


def memo_reference(memo: str) -> str:
    """Never log the memo itself; log a stable, one-way reference."""
    return hashlib.sha256(memo.encode("utf-8")).hexdigest()[:16]


def settle(order, amount_zats: int, wallet) -> None:
    wallet.send_payment(
        recipient=SHIELDED_UA,
        amount_zats=amount_zats,
        memo=f"order:{order.id}",
        # no explicit pool: the wallet prefers shielded notes (ZIP 315)
    )
    logger.info("settled order=%s memo_ref=%s", order.id, memo_reference(order.reference))


def invoice_uri(order_id: str, amount_zec: str) -> str:
    memo = base64.urlsafe_b64encode(f"order:{order_id}".encode()).decode().rstrip("=")
    return f"zcash:{SHIELDED_UA}?amount={amount_zec}&memo={memo}"
