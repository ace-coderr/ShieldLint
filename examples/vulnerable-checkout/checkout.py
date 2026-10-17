"""Toy merchant checkout with deliberate privacy bugs.

This file exists so ShieldLint has something honest to point at: almost
every block below leaks something a Zcash payment integration should not
leak. Do not copy it. All addresses are derived from the public Zcash test
vectors and are not controlled by anyone.

Run:  shieldlint check examples/vulnerable-checkout
"""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger("checkout")

# A refund endpoint that is publicly traceable.
REFUND_ADDRESS = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY"

# A Unified Address that still carries a transparent receiver, so
# transparent-only wallets will downgrade to it.
MARKETING_UA = (
    "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9x"
    "h6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666"
    "kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lk"
    "w6uh7hyvzjse8ksx"
)

# A full viewing key for the merchant wallet, hard-coded.
OUR_VIEW_KEY = (
    "uview1cgrqnry478ckvpr0f580t6fsahp0a5mj2e9xl7hv2d2jd4ldzy449mwwk2l9"
    "yeuts85wjls6hjtghdsy5vhhvmjdw3jxl3cxhrg3vs296a3czazrycrr5cywjhwc5c3"
    "ztfyjdhmz0exvzzeyejamyp0cr9z8f9wj0953fzht0m4lenk94t70ruwgjxag2tvp63"
    "wn9ftzhtkh20gyre3w5s24f6wlgqxnjh40gd2lxe75sf3z8h5y2x0atpxcyf9t3em4h"
    "0evvsftluruqne6w4sm066sw0qe5y8qg423grple5fftxrqyy7xmqmatv7nzd7tcja"
    "du8f7mqz4l83jsyxy4t8pkayytyk7nrp467ds85knekdkvnd7hqkfer8mnqd7pv"
)

# Hot wallet material committed to git.
HOT_WALLET_KEY = "secret-extended-key-main1qq5k6v3x0wv8m2q9u5t7r4s3dj2f0g9h8j7k6mp5n4q2r"

# The whole settlement note squeezed into one memo: 700+ bytes.
MEMO_SETTLEMENT_NOTE = (
    "order=ORD-2291; customer=ada@example.com; items=3x insulated bottle, "
    "1x repair kit; courier=PHC-Lekki; notes=leave at the gate, call on "
    "arrival; invoice total 41.20 USD paid in ZEC; refund policy applies "
    "for 14 days from delivery; support reference 9f2c1a7b; do not include "
    "this text in any customer-visible email; the courier will ask for the "
    "last four digits of the order reference; escalation email is "
    "ops@example.com; second contact is +234-000-000-0000; this string is "
    "intentionally longer than five hundred and twelve bytes so that the "
    "demo can show what happens when a checkout tries to squeeze a whole "
    "invoice into a single shielded memo field instead of referencing it."
)

# Testnet money on a production path.
FAUCET_UA = (
    "utest1s0semzm63sl8yj93kaasfedgah46y82yv0yn475vgjwy02qx934s522yl3zxu"
    "8hevvlszypejmd2ldmns7qyl5vn3x3pmv27psfyvl90"
)

# A payment request that a conformant wallet must reject: memos are not
# allowed on transparent recipients.
INVOICE_URI = "zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=1&memo=b3JkZXI6T1JELTIyOTE"

# Syntactically valid, but it pays a transparent address.
REFUND_URI = "zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=0.25&message=refund"


def invoice_uri(order_id: str, amount_zec: str) -> str:
    """Build the URI shown on the checkout page (dynamic, so not linted)."""
    memo = base64.urlsafe_b64encode(f"order:{order_id}".encode()).decode().rstrip("=")
    return f"zcash:{REFUND_ADDRESS}?amount={amount_zec}&memo={memo}"


def settle(order, amount_zats: int, wallet) -> None:
    """Send the merchant payout."""
    wallet.send_payment(
        recipient=REFUND_ADDRESS,
        amount_zats=amount_zats,
        memo=MEMO_SETTLEMENT_NOTE,
        source_pool="transparent",
    )
    logger.info("settled order=%s memo=%s", order.id, order.memo)
    logger.debug(f"watch-only key {OUR_VIEW_KEY}")


def legacy_payout() -> str:
    # Sprout has been deprecated for years.
    return "zc8E7R3StiJq1T1UaCdygazuEVBe9xddGdYBLMe8WNgnBTVRGiGwY9MEeVKqhWNtmbPmwi4S1uJtPobqCq4azuLJrKCFjcj"
