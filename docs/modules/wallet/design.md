# Wallet Module Design Document
## Copy-Trading Platform - `app.wallet`

### 1. Overview

The Wallet module manages exchange account deposit addresses for the copy-trading platform through CCXT integration. It provides multi-user support by imaging different exchange accounts and managing their associated deposit addresses across various supported exchanges. The module integrates with the Identity module's role-based access control system for secure operations.

### 2. Module Scope

**Primary Responsibilities:**
- Exchange account deposit address management (CRUD operations)
- Multi-exchange integration via CCXT library
- User-to-exchange account mapping and isolation
- Exchange API credential management
- Address synchronization with exchange platforms
- Role-based access control integration

**Out of Scope:**
- Direct blockchain network integration
- Private key generation or management
- Withdrawal processing and transaction execution
- Portfolio balance calculations (handled by trading module)
- Fiat currency operations
- User role management (handled by Identity module)

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

**Required Permissions:**
- `wallet_management:read` - View addresses and exchange accounts
- `wallet_management:write` - Create, update, delete addresses
- `wallet_management:sync` - Synchronize addresses with exchanges
- `wallet_management:admin` - Administrative operations on all accounts

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
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
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
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
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
    required_permissions JSONB DEFAULT '{}', -- Permissions needed per operation
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Address Sync Log
CREATE TABLE address_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id),
    user_id UUID NOT NULL REFERENCES users(id),
    initiated_by UUID NOT NULL REFERENCES users(id),
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
    INDEX idx_user_sync (user_id, created_at),
    INDEX idx_initiated_sync (initiated_by, created_at)
);

-- Address Activity Log
CREATE TABLE address_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address_id UUID NOT NULL REFERENCES exchange_deposit_addresses(id),
    user_id UUID NOT NULL REFERENCES users(id),
    performed_by UUID NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_address_activity (address_id, created_at),
    INDEX idx_user_activity (user_id, created_at),
    INDEX idx_performed_activity (performed_by, created_at)
);

-- Wallet Permission Requirements
CREATE TABLE wallet_operation_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation VARCHAR(100) NOT NULL UNIQUE,
    required_permission VARCHAR(100) NOT NULL,
    description TEXT,
    resource_level VARCHAR(50) DEFAULT 'user', -- 'user', 'account', 'system'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 4.2 API Endpoints

**Exchange Account Management:**
```
POST   /api/v1/wallet/exchanges              - Add new exchange account [wallet_management:write]
GET    /api/v1/wallet/exchanges              - List user's exchange accounts [wallet_management:read]
GET    /api/v1/wallet/exchanges/{id}         - Get exchange account details [wallet_management:read]
PUT    /api/v1/wallet/exchanges/{id}         - Update exchange account [wallet_management:write]
DELETE /api/v1/wallet/exchanges/{id}         - Remove exchange account [wallet_management:write]
POST   /api/v1/wallet/exchanges/{id}/test    - Test exchange API connection [wallet_management:read]
```

**Address CRUD Operations:**
```
POST   /api/v1/wallet/addresses              - Create/fetch new deposit address [wallet_management:write]
GET    /api/v1/wallet/addresses              - List user's addresses [wallet_management:read]
GET    /api/v1/wallet/addresses/{id}         - Get specific address details [wallet_management:read]
PUT    /api/v1/wallet/addresses/{id}         - Update address metadata [wallet_management:write]
DELETE /api/v1/wallet/addresses/{id}         - Remove address [wallet_management:write]
POST   /api/v1/wallet/addresses/sync         - Sync addresses from exchanges [wallet_management:sync]
```

**Address Management:**
```
POST   /api/v1/wallet/addresses/bulk         - Fetch multiple addresses [wallet_management:write]
GET    /api/v1/wallet/addresses/history/{id} - Get address activity history [wallet_management:read]
PUT    /api/v1/wallet/addresses/{id}/refresh - Refresh single address from exchange [wallet_management:sync]
GET    /api/v1/wallet/addresses/by-currency/{currency} - Get addresses by currency [wallet_management:read]
```

**Exchange Information:**
```
GET    /api/v1/wallet/exchanges/supported    - List supported exchanges [public]
GET    /api/v1/wallet/exchanges/{exchange_id}/currencies - Get supported currencies [wallet_management:read]
GET    /api/v1/wallet/exchanges/{exchange_id}/info - Get exchange information [wallet_management:read]
```

**Administrative Endpoints:**
```
GET    /api/v1/admin/wallet/exchanges        - List all exchange accounts [wallet_management:admin]
GET    /api/v1/admin/wallet/sync-status      - Get sync status across all accounts [wallet_management:admin]
POST   /api/v1/admin/wallet/sync/force       - Force sync for specific accounts [wallet_management:admin]
GET    /api/v1/admin/wallet/analytics        - Exchange usage analytics [wallet_management:admin]
GET    /api/v1/admin/wallet/users/{id}/accounts - Get user's exchange accounts [wallet_management:admin]
```

### 5. Permission Integration

#### 5.1 Permission Validation Middleware

```javascript
// Wallet-specific permission middleware
const requireWalletPermission = (operation, resourceLevel = 'user') => {
  return async (req, res, next) => {
    try {
      const user = req.user;
      const permissionRequired = await getOperationPermission(operation);
      
      // Check if user has required permission
      const hasPermission = await checkUserPermission(
        user.id, 
        'wallet_management', 
        permissionRequired
      );
      
      // Additional resource-level checks
      if (hasPermission && resourceLevel !== 'public') {
        const resourceAccess = await validateResourceAccess(
          user.id, 
          req.params, 
          resourceLevel
        );
        
        if (!resourceAccess) {
          return res.status(403).json({
            error: {
              code: 'RESOURCE_ACCESS_DENIED',
              message: 'Access denied to requested resource',
              timestamp: new Date().toISOString()
            }
          });
        }
      }
      
      // Log permission check
      await logWalletPermissionCheck(
        user.id, 
        operation, 
        permissionRequired, 
        hasPermission
      );
      
      if (!hasPermission) {
        return res.status(403).json({
          error: {
            code: 'INSUFFICIENT_WALLET_PERMISSIONS',
            message: `Access denied: requires wallet_management:${permissionRequired}`,
            operation: operation,
            timestamp: new Date().toISOString()
          }
        });
      }
      
      next();
    } catch (error) {
      next(error);
    }
  };
};

// Usage examples
app.post('/api/v1/wallet/exchanges', 
  requireWalletPermission('create_exchange_account', 'user'),
  createExchangeAccountController
);

app.get('/api/v1/admin/wallet/analytics', 
  requireWalletPermission('admin_analytics', 'system'),
  getWalletAnalyticsController
);
```

#### 5.2 Resource Access Validation

```javascript
class WalletAccessValidator {
  async validateResourceAccess(userId, params, resourceLevel) {
    switch (resourceLevel) {
      case 'user':
        return await this.validateUserResourceAccess(userId, params);
      case 'account':
        return await this.validateAccountResourceAccess(userId, params);
      case 'system':
        return await this.validateSystemResourceAccess(userId);
      default:
        return true; // Public access
    }
  }
  
  async validateUserResourceAccess(userId, params) {
    // Ensure user can only access their own resources
    if (params.user_id && params.user_id !== userId) {
      const hasAdminPermission = await checkUserPermission(
        userId, 
        'wallet_management', 
        'admin'
      );
      return hasAdminPermission;
    }
    
    // Validate exchange account ownership
    if (params.exchange_account_id) {
      const account = await getExchangeAccount(params.exchange_account_id);
      return account && account.user_id === userId;
    }
    
    // Validate address ownership
    if (params.address_id) {
      const address = await getDepositAddress(params.address_id);
      return address && address.user_id === userId;
    }
    
    return true;
  }
  
  async validateAccountResourceAccess(userId, params) {
    // Check if user has access to specific exchange account
    if (params.exchange_account_id) {
      const account = await getExchangeAccount(params.exchange_account_id);
      if (!account) return false;
      
      // Owner has access
      if (account.user_id === userId) return true;
      
      // Check if user has delegation or admin permissions
      return await checkAccountDelegation(userId, params.exchange_account_id);
    }
    
    return false;
  }
  
  async validateSystemResourceAccess(userId) {
    // Only users with admin permissions can access system-level resources
    return await checkUserPermission(
      userId, 
      'wallet_management', 
      'admin'
    );
  }
} 