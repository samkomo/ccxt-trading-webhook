# Authentication

The webhook supports two authentication methods: secure HMAC signatures with a timestamp header and a token-based fallback for environments where custom headers are not available (e.g. TradingView alerts).

## Environment Variables
```env
WEBHOOK_SECRET=your_shared_secret
DEFAULT_EXCHANGE=binance
DEFAULT_API_KEY=your_exchange_api_key
DEFAULT_API_SECRET=your_exchange_api_secret
LOG_LEVEL=INFO
RATE_LIMIT=10/minute
SIGNATURE_CACHE_TTL=300
SIGNATURE_CACHE_SIZE=1000
NONCE_TTL=300
TOKEN_TTL=86400
TOKEN_RATE_CACHE_SIZE=1000
REQUIRE_HTTPS=false
QUEUE_ORDERS=false
STATIC_API_KEY=
REQUIRE_API_KEY=false
TOKEN_DB_PATH=tokens.db
```

| Variable | Description |
|--------------------|-------------|
| `WEBHOOK_SECRET`   | Shared secret for HMAC or token |
| `DEFAULT_EXCHANGE` | Fallback exchange |
| `DEFAULT_API_KEY`  | Optional fallback key |
| `DEFAULT_API_SECRET` | Optional fallback secret |
| `LOG_LEVEL`        | Logging verbosity |
| `RATE_LIMIT`       | Requests allowed per timeframe |
| `SIGNATURE_CACHE_TTL` | Cache TTL for replay-protection signatures |
| `SIGNATURE_CACHE_SIZE` | Maximum entries for signature cache |
| `NONCE_TTL` | Expiration time for stored nonces (seconds) |
| `TOKEN_TTL` | Expiration time for issued tokens (seconds) |
| `TOKEN_RATE_CACHE_SIZE` | Maximum tracked tokens for rate limiting |
| `REQUIRE_HTTPS` | Reject plain HTTP requests when set to `true` |
| `QUEUE_ORDERS` | Enqueue orders to Celery when enabled |
| `STATIC_API_KEY` | API key expected in the `X-API-Key` header |
| `REQUIRE_API_KEY` | Enable static API key verification |
| `TOKEN_DB_PATH` | Path to SQLite file storing tokens |

## Webhook Payload Format
### Secure Mode
Use headers:
| Header | Description |
|--------|-------------|
| `X-Timestamp` | Unix time in seconds |
| `X-Signature` | HMAC SHA256 using `WEBHOOK_SECRET` |

Generate signature:
```python
hmac.new(secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
```

### Token Fallback Mode
Use this when custom headers can't be set (e.g., TradingView):
```json
{
  "token": "issued_token_here",
  "nonce": "unique_id",
  ...
}
```
Include a new random `nonce` value with each request to prevent replay attacks.

**Issuing a Token**
```bash
python manage_tokens.py issue --ttl 3600
```
The command prints the token value which should be used in TradingView alerts.

**Revoking a Token**
```bash
python manage_tokens.py revoke <token>
```
Expired tokens are automatically cleaned up during verification.

## Identity API Endpoints

The identity service exposes REST endpoints for user onboarding and token management.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `POST` | `/api/v1/identity/register` | Create a new user account |
| `POST` | `/api/v1/identity/login` | Obtain an auth token |
| `GET`  | `/api/v1/identity/profile` | Retrieve the current profile |
| `POST` | `/api/v1/identity/tokens` | Create an API token |
| `GET`  | `/api/v1/identity/tokens` | List issued tokens |

See the [API reference](api-reference.md) for payload details.

