# TradingView Integration

Set the webhook URL in your TradingView alert to `https://your-app.herokuapp.com/webhook`.
Paste the following message as **one-line JSON**:
```json
{
  "token": "issued_token_here",
  "nonce": "unique_id",
  "exchange": "{{exchange}}",
  "apiKey": "your_api_key",
  "secret": "your_api_secret",
  "symbol": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "amount": "{{strategy.order.contracts}}",
  "price": "{{close}}"
}
```
Make sure each alert uses a unique `nonce` value.

## Common Variables
| Variable | Description |
|------------------------------|--------------------------------------------------|
| `{{strategy.order.action}}`  | `"buy"` or `"sell"` depending on strategy signal |
| `{{strategy.order.id}}`      | Custom order ID from Pine script |
| `{{strategy.position_size}}` | Size of the current position |
| `{{strategy.order.contracts}}`| Number of contracts/units in the order |
| `{{close}}`                  | Close price of the current candle |
| `{{ticker}}`                 | Trading pair (e.g., `BTCUSDT`) |
| `{{exchange}}`               | Exchange name (e.g., `BINANCE`) |
| `{{time}}`                   | UNIX timestamp of the candle |
