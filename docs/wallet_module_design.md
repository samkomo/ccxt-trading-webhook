# Wallet Module Design Document
## Copy-Trading Platform - `app.wallet`

### 1. Overview

The Wallet module manages exchange account deposit addresses for the copy-trading platform through CCXT integration. It provides multi-user support by imaging different exchange accounts and managing their associated deposit addresses across various supported exchanges.

### 2. Module Scope

**Primary Responsibilities:**
- Exchange account deposit address management (CRUD operations)
- Multi-exchange integration via CCXT library
- User-to-exchange account mapping and isolation
- Exchange API credential management
- Address synchronization with exchange platforms

**Out of Scope:**
- Direct blockchain network integration
- Private key generation or management
- Withdrawal processing and transaction execution
- Portfolio balance calculations (handled by trading module)
- Fiat currency operations

### 3. Core Features

#### 3.1 Address CRUD Operations

**Purpose:** Manage deposit addresses obtained from various cryptocurrency exchanges through CCXT integration.

**Key Capabilities:**
- Fetch and store deposit addresses from exchanges
- List user's exchange deposit addresses
- Update address metadata and labels
- Refresh addresses from exchange APIs
- Address validation through exchange verification
- Multi-exchange address management

**Supported Address Operations:**
- **Create:** Fetch new deposit addresses from exchanges via CCXT
- **Read:** Retrieve cached address details or list multiple addresses
- **Update:** Modify address labels, status, and user-defined metadata
- **Delete:** Remove address associations while maintaining audit trail

#### 3.2 Multi-Exchange Support via CCXT

**Purpose:** Support deposit addresses across major cryptocurrency exchanges.

**Supported Exchanges:**
- **Binance:** Spot and futures deposit addresses
- **Coinbase Pro:** Professional trading deposit addresses
- **Kraken:** Comprehensive deposit address support
- **Bitfinex:** Multi-currency deposit addresses
- **Huobi:** Global exchange deposit addresses
- **KuCoin:** Wide cryptocurrency support
- **Bybit:** Derivatives and spot deposit addresses
- **OKX:** Comprehensive trading platform addresses

#### 3.3 Exchange Account Imaging

**Purpose:** Create isolated exchange account instances for different users.

**Key Features:**
- User-specific exchange API credential management
- Sandboxed exchange account operations
- Multi-user address isolation
- Exchange-specific configuration management
- Rate limiting per user per exchange
- Error handling and retry mechanisms

### 4. Technical Architecture

#### 4.1 Database Schema

```sql
-- Exchange Accounts
CREATE TABLE exchange_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    exchange_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    api_passphrase_encrypted TEXT,
    sandbox_mode BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, exchange_id, account_name),
    INDEX idx_user_exchanges (user_id, is_active),
    INDEX idx_exchange_sync (exchange_id, last_sync_at)
);

-- Exchange Deposit Addresses
CREATE TABLE exchange_deposit_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id),
    user_id UUID NOT NULL REFERENCES users(id),
    exchange_id VARCHAR(50) NOT NULL,
    currency VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    tag VARCHAR(100), -- For currencies that require memo/tag
    network VARCHAR(50),
    address_type VARCHAR(20) DEFAULT 'deposit',
    label VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    exchange_metadata JSONB DEFAULT '{}',
    user_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(exchange_account_id, currency, address),
    INDEX idx_user_addresses (user_id, is_active),
    INDEX idx_exchange_currency (exchange_id, currency),
    INDEX idx_address_lookup (address, exchange_id)
);

-- Supported Exchanges
CREATE TABLE supported_exchanges (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ccxt_id VARCHAR(50) NOT NULL UNIQUE,
    website_url VARCHAR(255),
    api_doc_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    supports_deposit_addresses BOOLEAN DEFAULT TRUE,
    rate_limit_per_minute INTEGER DEFAULT 60,
    requires_passphrase BOOLEAN DEFAULT FALSE,
    sandbox_available BOOLEAN DEFAULT FALSE,
    supported_currencies TEXT[], -- Array of supported currency codes
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Address Sync Log
CREATE TABLE address_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id),
    user_id UUID NOT NULL REFERENCES users(id),
    sync_type VARCHAR(50) NOT NULL, -- 'full', 'incremental', 'single_currency'
    currencies_synced TEXT[],
    addresses_added INTEGER DEFAULT 0,
    addresses_updated INTEGER DEFAULT 0,
    addresses_removed INTEGER DEFAULT 0,
    sync_duration_ms INTEGER,
    status VARCHAR(20) NOT NULL, -- 'success', 'partial', 'failed'
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_sync_history (exchange_account_id, created_at),
    INDEX idx_user_sync (user_id, created_at)
);

-- Address Activity Log
CREATE TABLE address_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_id UUID NOT NULL REFERENCES exchange_deposit_addresses(id),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_address_activity (address_id, created_at),
    INDEX idx_user_activity (user_id, created_at)
);
```

#### 4.2 API Endpoints

**Exchange Account Management:**
```
POST   /api/v1/wallet/exchanges              - Add new exchange account
GET    /api/v1/wallet/exchanges              - List user's exchange accounts
GET    /api/v1/wallet/exchanges/{id}         - Get exchange account details
PUT    /api/v1/wallet/exchanges/{id}         - Update exchange account
DELETE /api/v1/wallet/exchanges/{id}         - Remove exchange account
POST   /api/v1/wallet/exchanges/{id}/test    - Test exchange API connection
```

**Address CRUD Operations:**
```
POST   /api/v1/wallet/addresses              - Create/fetch new deposit address
GET    /api/v1/wallet/addresses              - List user's addresses
GET    /api/v1/wallet/addresses/{id}         - Get specific address details
PUT    /api/v1/wallet/addresses/{id}         - Update address metadata
DELETE /api/v1/wallet/addresses/{id}         - Remove address
POST   /api/v1/wallet/addresses/sync         - Sync addresses from exchanges
```

**Address Management:**
```
POST   /api/v1/wallet/addresses/bulk         - Fetch multiple addresses
GET    /api/v1/wallet/addresses/history/{id} - Get address activity history
PUT    /api/v1/wallet/addresses/{id}/refresh - Refresh single address from exchange
GET    /api/v1/wallet/addresses/by-currency/{currency} - Get addresses by currency
```

**Exchange Information:**
```
GET    /api/v1/wallet/exchanges/supported    - List supported exchanges
GET    /api/v1/wallet/exchanges/{exchange_id}/currencies - Get supported currencies
GET    /api/v1/wallet/exchanges/{exchange_id}/info - Get exchange information
```

**Admin Endpoints:**
```
GET    /api/v1/admin/wallet/exchanges        - List all exchange accounts
GET    /api/v1/admin/wallet/sync-status      - Get sync status across all accounts
POST   /api/v1/admin/wallet/sync/force       - Force sync for specific accounts
GET    /api/v1/admin/wallet/analytics        - Exchange usage analytics
```

### 5. CCXT Integration Architecture

#### 5.1 Exchange Client Management

```javascript
// Exchange client factory with user isolation
class ExchangeClientManager {
  constructor() {
    this.clients = new Map(); // user_id:exchange_id -> ccxt_instance
    this.rateLimiters = new Map();
  }

  async getClient(userId, exchangeAccountId) {
    const key = `${userId}:${exchangeAccountId}`;
    
    if (!this.clients.has(key)) {
      const account = await this.getExchangeAccount(exchangeAccountId);
      const client = this.createCCXTClient(account);
      this.clients.set(key, client);
    }
    
    return this.clients.get(key);
  }

  createCCXTClient(account) {
    const ExchangeClass = ccxt[account.exchange_id];
    return new ExchangeClass({
      apiKey: decrypt(account.api_key_encrypted),
      secret: decrypt(account.api_secret_encrypted),
      password: account.api_passphrase_encrypted ? 
                decrypt(account.api_passphrase_encrypted) : undefined,
      sandbox: account.sandbox_mode,
      enableRateLimit: true,
      rateLimit: this.getRateLimit(account.exchange_id)
    });
  }
}
```

#### 5.2 Address Synchronization Service

```javascript
class AddressSyncService {
  async syncAddresses(exchangeAccountId, currencies = null) {
    const client = await this.exchangeManager.getClient(userId, exchangeAccountId);
    const syncLog = await this.createSyncLog(exchangeAccountId, currencies);
    
    try {
      const supportedCurrencies = currencies || 
        await this.getSupportedCurrencies(client);
      
      for (const currency of supportedCurrencies) {
        try {
          const address = await client.fetchDepositAddress(currency);
          await this.upsertAddress(exchangeAccountId, currency, address);
          syncLog.addresses_added++;
        } catch (error) {
          await this.logSyncError(syncLog, currency, error);
        }
      }
      
      syncLog.status = 'success';
    } catch (error) {
      syncLog.status = 'failed';
      syncLog.error_details = { error: error.message };
    }
    
    await this.updateSyncLog(syncLog);
  }
}
```

### 6. Security Considerations

#### 6.1 API Credential Security
- AES-256 encryption for API keys and secrets
- Secure key management with rotation capabilities
- Environment-specific encryption keys
- Hardware security module (HSM) integration
- API credential validation and testing

#### 6.2 Multi-User Isolation
- User-specific exchange client instances
- Sandboxed API operations per user
- Rate limiting per user per exchange
- Access control and permission validation
- Audit logging for all operations

#### 6.3 Exchange API Security
- SSL/TLS enforcement for all API calls
- API key permission validation
- Retry mechanisms with exponential backoff
- Error handling and graceful degradation
- Monitoring for API abuse patterns

### 7. Performance Requirements

- Address fetching: < 2s per currency per exchange
- Address listing: < 200ms response time (paginated)
- Address sync: < 30s for full account sync
- Exchange connection test: < 5s response time
- Concurrent operations: 100+ requests/second per user
- Database queries: < 50ms for address lookups
- API rate limiting: Respect exchange-specific limits

### 8. Monitoring & Observability

#### 8.1 Key Metrics
- Address sync success/failure rates by exchange
- API call response times and error rates
- Exchange account connection status
- Address creation and update frequencies
- Rate limiting incidents
- User activity patterns by exchange

#### 8.2 Alerting
- Exchange API connection failures
- Sync operation failures exceeding threshold
- Rate limiting violations
- API credential expiration warnings
- Unusual address activity patterns
- Exchange service disruptions

### 9. Error Handling

#### 9.1 Common Error Scenarios
- Exchange API connection failures
- Invalid or expired API credentials
- Rate limiting exceeded
- Unsupported currency/exchange combinations
- Network connectivity issues
- Exchange maintenance periods
- Insufficient API permissions

#### 9.2 Error Response Format
```json
{
  "error": {
    "code": "EXCHANGE_API_ERROR",
    "message": "Failed to fetch deposit address from exchange",
    "details": {
      "exchange": "binance",
      "currency": "BTC",
      "exchange_error": "Invalid API key",
      "retry_after": 300
    },
    "timestamp": "2024-01-20T14:25:00Z"
  }
}
```

### 10. Integration Points

#### 10.1 Internal Dependencies
- **Identity Module:** User authentication and authorization
- **Trading Engine:** Exchange account validation for trading
- **Notification Service:** Sync status and error notifications
- **Admin Dashboard:** Exchange account and address management
- **Audit Service:** Comprehensive logging of wallet operations

#### 10.2 External Services
- **CCXT Library:** Unified exchange API integration
- **Exchange APIs:** Direct integration with exchange platforms
- **Encryption Services:** API credential protection
- **Monitoring Services:** Exchange connectivity monitoring
- **Rate Limiting Services:** API usage control

### 11. Future Enhancements

- Real-time address balance monitoring
- Multi-signature address support
- Address pool management for high-volume users
- Advanced exchange account analytics
- Automated API credential rotation
- Integration with additional exchanges
- Address whitelisting and blacklisting
- Cross-exchange address management

### 12. Testing Strategy

#### 12.1 Unit Tests
- CCXT client initialization and configuration
- Address CRUD operations
- Exchange account management
- API credential encryption/decryption
- Error handling and retry logic

#### 12.2 Integration Tests
- End-to-end address synchronization
- Exchange API connectivity tests
- Multi-user isolation verification
- Rate limiting compliance
- Error recovery scenarios

#### 12.3 Exchange-Specific Tests
- Address format validation per exchange
- Currency support verification
- API rate limit adherence
- Sandbox mode functionality
- Error message handling per exchange