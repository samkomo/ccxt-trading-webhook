# Identity Module

This module provides user onboarding, authentication and compliance features for the platform.

See the [Design Doc](../identity_module_design.md) and [Implementation Plan](../identity-implementation-plan.md) for in‑depth architecture. Endpoint details are available in the [Authentication guide](../authentication.md#identity-api-endpoints) and [API reference](../api-reference.md#identity-endpoints).

## User Account Types
- **Standard** – email based registration with password verification.
- **Social** – OAuth providers such as Google and Apple.
- **Institutional** – enhanced verification for business accounts.
- **Demo** – limited accounts for trial access.

### Registration Example
```python
import requests
payload = {
    "email": "user@example.com",
    "username": "demo",
    "password": "s3cret",
    "registration_type": "standard"
}
resp = requests.post("https://api.example.com/api/v1/identity/register", json=payload)
print(resp.json())
```

### Social Login Example
```python
import requests
payload = {
    "email": "google@example.com",
    "username": "guser",
    "registration_type": "social"
}
resp = requests.post("https://api.example.com/api/v1/identity/register", json=payload)
print(resp.json())
```

## Role Hierarchy
Built‑in roles are defined in the [design document](../identity_module_design.md#3.2-role-based-access-control-rbac). Roles include `super_admin`, `admin`, `kyc_reviewer`, `compliance_officer`, `support_agent`, `trader`, `viewer` and `demo_user`.

### Assigning a Role
```python
import requests
headers = {"Authorization": "Bearer <access_token>"}
resp = requests.post(
    "https://api.example.com/api/v1/admin/identity/users/<user_id>/roles",
    headers=headers,
    json={"role_id": "trader"}
)
print(resp.json())
```

## Token Management
Tokens control API access with optional TTL and role restrictions. For implementation details see the [token section](../identity_module_design.md#3.3-token-management).

### Create Token
```python
import requests
headers = {"Authorization": "Bearer <access_token>"}
resp = requests.post(
    "https://api.example.com/api/v1/identity/tokens",
    headers=headers,
    json={
        "token_name": "bot-token",
        "token_type": "trading",
        "permissions": {"orders": ["create"]},
        "expires_in": 86400
    }
)
print(resp.json())
```

## KYC Levels
The system supports `basic`, `intermediate` and `advanced` verification flows. Documents are uploaded and reviewed by admins as outlined in the [implementation plan](../identity-implementation-plan.md#4-kyc-workflow).

### KYC Review Example
```python
import requests
headers = {"Authorization": "Bearer <admin_token>"}
resp = requests.put(
    "https://api.example.com/api/v1/admin/identity/kyc/<kyc_id>/approve",
    headers=headers
)
print(resp.json())
```

## Security Considerations
- Enforce HTTPS in production.
- Enable multi‑factor authentication for token creation.
- Uploaded files are scanned for viruses.
More security notes are provided in the [design doc](../identity_module_design.md#6-security) and [implementation plan](../identity-implementation-plan.md#6-security).

## API References
- [Authentication Guide](../authentication.md#identity-api-endpoints)
- [Full API Reference](../api-reference.md#identity-endpoints)

## Integration Patterns
Identity integrates with the wallet, compliance and dashboard modules. The [design document](../identity_module_design.md#7-integrations) covers these flows in detail.

## Troubleshooting
- **Registration failed** – ensure the email is not already in use.
- **Invalid login** – verify credentials and that the account is activated.
- **Token errors** – check if the token is revoked or expired.
- **KYC pending** – confirm that all required documents were uploaded.

