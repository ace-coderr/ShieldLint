//! Minimal payout helper used by the ShieldLint demo.
//!
//! Links for the demo: the treasury address is a Unified Address that still
//! carries a transparent receiver, and the invoice URI pays a t-address.

use zcash_primitives::transaction::TxId;

/// Unified Address with a transparent receiver: transparent-only senders
/// will pick it, making the payment public.
pub const TREASURY_UA: &str = "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9xh6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lkw6uh7hyvzjse8ksx";

/// A payment request that pays a transparent address.
pub const INVOICE_URI: &str = "zcash:t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY?amount=0.5";

pub fn pay(invoice: &Invoice) -> Result<TxId, Error> {
    // Spending public UTXOs publishes the input side of the transaction.
    let source = Source::Transparent;
    let fee_rule = StandardFeeRule::Zip317;

    println!("memo: {}", invoice.memo);
    // shieldlint: ignore[SL005]
    println!("debug memo: {}", invoice.memo);

    build_and_send(source, fee_rule, TREASURY_UA, invoice)
}
