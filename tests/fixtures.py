"""Address constants used by the test-suite.

All values are derived from the public Zcash test vectors
(https://github.com/zcash/zcash-test-vectors) and are not controlled by
anyone. They exist to exercise the decoder and the rules.
"""

#: mainnet transparent P2PKH
TADDR = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRY"
#: same, one character changed: fails Base58Check
TADDR_BAD = "t1cN2ZVWzWcVRrnfeQzmkpLhzQ4dYRv8yRZ"

#: Unified Address with transparent + sapling + orchard receivers (revision 0)
UA_WITH_TRANSPARENT = (
    "u1pg2aaph7jp8rpf6yhsza25722sg5fcn3vaca6ze27hqjw7jvvhhuxkpcg0ge9xh6drsgdkda8qjq5chpehkcpxf87rnjryjqwymdheptpvnljqqrjqzjwkc2ma6hcq666kgwfytxwac8eyex6ndgr6ezte66706e3vaqrd25dzvzkc69kw0jgywtd0cmq52q5lkw6uh7hyvzjse8ksx"
)
#: shielded-only Unified Address (revision 2, `zu` prefix)
UA_SHIELDED = (
    "zu175e9thzutjjcqe9u3ca0n98msdagd8hp5vpl2zex065dzmmkf8pftgklq4upnrm5v3et4t89pffvat49xp3xw6mp2yzf9te8tjr7hhsz03x9w30vapxzh3u5eewdmrtc07fsepvnarvvma9tvvuw3ke57unafx2tg9l728h3m5uhhle3"
)
#: testnet Unified Address
UA_TESTNET = (
    "utest1s0semzm63sl8yj93kaasfedgah46y82yv0yn475vgjwy02qx934s522yl3zxu8hevvlszypejmd2ldmns7qyl5vn3x3pmv27psfyvl90"
)
#: mainnet Sapling address
SAPLING = "zs1mrhc9y7jdh5r9ece8u5khgvj9kg0zgkxzdduyv0whkg7lkcrkx5xqem3e48avjq9wn2rukydkwn"
#: legacy Sprout address
SPROUT = (
    "zc8E7R3StiJq1T1UaCdygazuEVBe9xddGdYBLMe8WNgnBTVRGiGwY9MEeVKqhWNtmbPmwi4S1uJtPobqCq4azuLJrKCFjcj"
)
#: Unified full viewing key (public test vector)
UFVK = (
    "uview1cgrqnry478ckvpr0f580t6fsahp0a5mj2e9xl7hv2d2jd4ldzy449mwwk2l9yeuts85wjls6hjtghdsy5vhhvmjdw3jxl3cxhrg3vs296a3czazrycrr5cywjhwc5c3ztfyjdhmz0exvzzeyejamyp0cr9z8f9wj0953fzht0m4lenk94t70ruwgjxag2tvp63wn9ftzhtkh20gyre3w5s24f6wlgqxnjh40gd2lxe75sf3z8h5y2x0atpxcyf9t3em4h0evvsftluruqne6w4sm066sw0qe5y8qg423grple5fftxrqyy7xmqmatv7nzd7tcjadu8f7mqz4l83jsyxy4t8pkayytyk7nrp467ds85knekdkvnd7hqkfer8mnqd7pv"
)
#: what a leaked Sapling spending key looks like (fabricated, bech32 charset only)
SECRET = "secret-extended-key-main1qq5k6v3x0wv8m2q9u5t7r4s3dj2f0g9h8j7k6mp5n4q2r"

URI_SHIELDED = f"zcash:{UA_SHIELDED}?amount=0.5&memo=b3JkZXI6MQ"
URI_TRANSPARENT = f"zcash:{TADDR}?amount=0.25"
URI_MEMO_ON_TADDR = f"zcash:{TADDR}?amount=1&memo=b3JkZXI6MQ"
URI_BAD_AMOUNT = f"zcash:{UA_SHIELDED}?amount=1.234567890"

MEMO_LONG = "x" * 600
