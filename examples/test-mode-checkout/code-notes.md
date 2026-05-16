# Checkout Surface

The checkout flow currently supports:

- payment methods: credit card, PayPal, Apple Pay
- regions: US and UK
- currencies: USD and GBP
- operating systems: macOS and Windows
- browsers: Chrome and Safari
- loyalty tier: none or gold

Behavioral rules:

- Apple Pay is only supported on macOS
- Safari is only supported on macOS in this slice
- gold loyalty requires credit card so the reward can be stored
- card type only matters when payment method is credit card
- Apple Pay plus UK must not produce USD
- we want at least one generated case for Apple Pay on Safari on macOS
