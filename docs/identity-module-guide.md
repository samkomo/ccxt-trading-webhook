# Identity Module: Description and Usage Guide

## Module Overview

The Identity module serves as the foundational security and user management layer for the copy-trading platform. It handles user authentication, authorization, role-based access control, and regulatory compliance through KYC verification processes.

### Purpose
- **Who can access the platform?** - User registration and authentication
- **What can they do?** - Role-based permissions and access control
- **Are they legitimate?** - KYC verification and compliance
- **How do they interact?** - API token management for secure integrations

### Core Responsibilities
- User lifecycle management (registration, authentication, profile management)
- Role-based access control (RBAC) with hierarchical permissions
- API token generation and validation for secure system interactions
- KYC document collection and verification workflows
- Audit logging for compliance and security monitoring

## Key Capabilities

### 1. User Management
**Registration & Authentication**
- Email and phone-based account creation
- Password-based authentication with secure hashing
- Email verification and account activation
- Profile management and updates
- Account deactivation and deletion

**Supported Account Types**
- **Traders**: Create strategies, manage followers, earn from profit-sharing
- **Investors**: Follow strategies, manage investments, deposit/withdraw funds
- **Admins**: Platform management, user oversight, compliance monitoring

### 2. Role-Based Access Control
**Role System**
- **Trader**: Strategy creation, follower management, performance tracking
- **Investor**: Strategy browsing, subscription management, portfolio viewing
- **Admin**: User management, KYC review, system administration
- **Support**: Customer service operations, limited user assistance

**Permission Framework**
- Resource-action based permissions (e.g., `user_management:read`)
- Role inheritance and hierarchical permissions
- Dynamic permission checking with middleware
- Audit logging for all permission checks

### 3. API Token Management
**Token Types**
- **Personal Access Tokens**: Long-lived tokens for user applications
- **Webhook Tokens**: TradingView integration for strategy signals
- **Trading Tokens**: Secure access for copy-trading operations
- **Admin Tokens**: Elevated permissions for administrative tasks

**Security Features**
- Configurable expiration times
- Role-based token restrictions
- Usage tracking and analytics
- Secure revocation and blacklisting

### 4. KYC Verification
**Verification Levels**
- **Basic**: Phone verification + government ID
- **Intermediate**: Enhanced verification for strategy providers
- **Advanced**: Full compliance verification for high-value accounts

**Document Processing**
- Secure file upload with encryption
- OCR text extraction and validation
- Admin review workflow
- Compliance reporting and audit trails

## User Personas and Workflows

### Trader Journey
```
Registration → Email Verification → KYC (Intermediate) → Role Assignment → \
Webhook Token Creation → Strategy Listing → Follower Management
```

### Investor Journey
```
Registration → Phone Verification → KYC (Basic) → Role Assignment → \
Mobile Token Creation → Strategy Browsing → Investment Management
```

### Admin Journey
```
Admin Account Creation → Super Admin Role → System Access Token → \
User Management → KYC Review → Platform Oversight
```

## API Payloads and Responses

The following examples show common Identity API interactions. For a complete list of endpoints see the [API reference](api-reference.md#identity-endpoints).

### User Registration
```json
POST /api/v1/identity/register
{
  "email": "trader@example.com",
  "username": "crypto_trader_pro",
  "password": "secure_password",
  "first_name": "John",
  "last_name": "Trader",
  "phone_number": "+254700000000",
  "country_code": "KE"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "trader@example.com",
    "username": "crypto_trader_pro",
    "account_status": "pending_verification",
    "created_at": "2024-01-20T10:30:00Z"
  },
  "message": "Registration successful. Please check your email for verification."
}
```

### Email Verification
```json
POST /api/v1/identity/verify-email
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### User Login
```json
POST /api/v1/identity/login
{
  "email": "trader@example.com",
  "password": "secure_password"
}
```

**Response**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "user": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "trader@example.com",
      "username": "crypto_trader_pro",
      "roles": ["trader"],
      "kyc_status": "approved"
    }
  }
}
```

### Token Creation
```json
POST /api/v1/identity/tokens
Authorization: Bearer {user_access_token}
{
  "token_name": "TradingView Webhook",
  "token_type": "webhook",
  "permissions": {
    "trading_operations": ["create_signal", "update_strategy"]
  },
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### KYC Submission
```json
POST /api/v1/identity/kyc
Authorization: Bearer {user_access_token}
{
  "kyc_level": "intermediate"
}
```

### KYC Document Upload
```json
POST /api/v1/identity/kyc/documents
Authorization: Bearer {user_access_token}
Content-Type: multipart/form-data
{
  "kyc_verification_id": "kyc_123e4567-e89b-12d3-a456-426614174000",
  "document_type": "government_id",
  "file": {binary_file_data}
}
```

### Role Assignment (Admin)
```json
POST /api/v1/identity/users/{user_id}/roles
Authorization: Bearer {admin_token}
{
  "role_id": "role_trader_uuid"
}
```

### Get User Profile
```json
GET /api/v1/identity/profile
Authorization: Bearer {user_access_token}
```

### KYC Approval (Admin)
```json
PUT /api/v1/admin/identity/kyc/{kyc_id}/approve
Authorization: Bearer {admin_token}
{
  "compliance_score": 95,
  "notes": "All documents verified successfully"
}
```

### Token Revocation
```json
DELETE /api/v1/identity/tokens/{token_id}
Authorization: Bearer {user_access_token}
```

## Integration with Other Modules

- **Wallet Module Integration** — Validates user identity before deposit/withdrawal operations.
- **Trading Module Integration** — Verifies trader permissions and subscription status.
- **Execution Module Integration** — Authenticates TradingView webhooks and logs actions.
- **Operations Module Integration** — Supplies user identity data for compliance reports and analytics.

## Security Considerations
- Passwords hashed with bcrypt (minimum 12 rounds).
- JWT tokens with secure secrets and reasonable expiration.
- Principle of least privilege enforced via RBAC.
- KYC documents encrypted at rest.

## Troubleshooting
- **Token Validation Failures** — Check token expiration and permission scope.
- **Permission Denied Errors** — Verify user roles and permission hierarchy.
- **KYC Upload Failures** — Validate file size, format and encryption settings.
- **Registration Issues** — Ensure email/phone uniqueness and verification requirements.

For detailed design information see the [Identity Module Design Document](identity_module_design.md) and [Implementation Plan](identity-implementation-plan.md).
