# Wallet Module Design Document
## Copy-Trading Platform - `app.wallet`

### 1. Overview

The Wallet module manages a hybrid liquidity provider system where developers act as strategy managers with exchange accounts, while regular users participate through M-Pesa deposits in KES. The module handles address management for both M-Pesa settlements and developer exchange accounts, facilitating seamless copy-trading between traditional Kenyan payments and cryptocurrency markets.

### 2. Module Scope

**Primary Responsibilities:**
- M-Pesa wallet address management for regular users and developers
- Developer exchange account deposit address management via CCXT
- Liquidity pool address coordination and settlement tracking
- KES-denominated position tracking for regular users
- Settlement address management between pools and M-Pesa accounts

**Out of Scope:**
- KES to crypto conversion logic (handled by developers externally)
- Trading strategy execution (handled by trading engine)
- Profit calculation and distribution (handled by settlements module)
- M-Pesa API integration (handled by payments module)

### 3. User Types & Address Management

#### 3.1 Regular Users (Non-Technical)
**Wallet Structure:**
- Primary M-Pesa wallet address for deposits/withdrawals
- Virtual KES balance tracking
- Pool participation addresses (which developer strategies they're following)
- Settlement addresses for profit distribution

#### 3.2 Developers (Technical Users)
**Wallet Structure:**
- M-Pesa settlement address for receiving pooled funds and sending profits
- Exchange deposit addresses via CCXT integration
- Pool management addresses for tracking user funds
- Strategy-specific wallet addresses

### 4. Core Features

#### 4.1 Address CRUD Operations

**Purpose:** Manage wallet addresses for both user types across M-Pesa and exchange platforms.

**Regular User Address Management:**
- M-Pesa phone number as primary wallet address
- Pool participation tracking addresses
- Settlement history addresses
- KES balance tracking addresses

**Developer Address Management:**
- M-Pesa settlement addresses for fund reception
- Exchange deposit addresses via CCXT for each supported exchange
- Pool-specific addresses for segregated fund management
- Strategy wallet addresses for tracking performance

**Supported Address Operations:**
- **Create:** Generate M-Pesa addresses, fetch exchange addresses via CCXT
- **Read:** Retrieve address details, balances, and pool associations
- **Update:** Modify address metadata, pool associations, settlement preferences
- **Delete:** Deactivate addresses while maintaining audit trail

#### 4.2 Liquidity Pool Address Management

**Purpose:** Track fund flows between regular users, developers, and exchanges.

**Key Features:**
- Pool-specific address generation for each developer strategy
- Fund tracking from regular users to developer pools
- Settlement address management for profit distribution
- Cross-reference between M-Pesa and exchange addresses
- Pool balance reconciliation addresses

### 5. Technical Architecture

#### 5.1 Database Schema

```sql
-- User Wallet Addresses
CREATE TABLE user_wallet_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    user_type VARCHAR(20) NOT NULL, -- 'regular', 'developer'
    address_type VARCHAR(30) NOT NULL, -- 'mpesa_primary', 'mpesa_settlement', 'exchange_deposit', 'pool_tracking'
    address_value VARCHAR(255) NOT NULL, -- Phone number for M-Pesa, crypto address for exchanges
    label VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, address_type, address_value),
    INDEX idx_user_addresses (user_id, user_type, is_active),
    INDEX idx_address_lookup (address_value, address_type)
);

-- Developer Exchange Accounts
CREATE TABLE developer_exchange_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    developer_id UUID NOT NULL REFERENCES users(id),
    exchange_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    api_passphrase_encrypted TEXT,
    mpesa_settlement_address VARCHAR(15) NOT NULL, -- Phone number
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(developer_id, exchange_id, account_name),
    INDEX idx_developer_exchanges (developer_id, is_active)
);

-- Exchange Deposit Addresses (for developers)
CREATE TABLE exchange_deposit_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_account_id UUID NOT NULL REFERENCES developer_exchange_accounts(id),
    developer_id UUID NOT NULL REFERENCES users(id),
    exchange_id VARCHAR(50) NOT NULL,
    currency VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    tag VARCHAR(100), -- For currencies requiring memo/tag
    network VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    exchange_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(exchange_account_id, currency, address),
    INDEX idx_developer_addresses (developer_id, currency),
    INDEX idx_exchange_addresses (exchange_id, currency)
);

-- Liquidity Pool Addresses
CREATE TABLE liquidity_pool_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID NOT NULL, -- References strategy pools
    developer_id UUID NOT NULL REFERENCES users(id),
    address_type VARCHAR(30) NOT NULL, -- 'mpesa_collection', 'mpesa_distribution', 'exchange_trading'
    address_value VARCHAR(255) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KES',
    exchange_id VARCHAR(50), -- NULL for M-Pesa addresses
    is_active BOOLEAN DEFAULT TRUE,
    pool_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(pool_id, address_type, address_value),
    INDEX idx_pool_addresses (pool_id, developer_id),
    INDEX idx_pool_type (address_type, currency)
);

-- Regular User Pool Participation
CREATE TABLE user_pool_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    pool_id UUID NOT NULL,
    developer_id UUID NOT NULL REFERENCES users(id),
    mpesa_address VARCHAR(15) NOT NULL, -- User's M-Pesa phone number
    pool_entry_address VARCHAR(255), -- Virtual tracking address
    allocation_amount DECIMAL(15,2) DEFAULT 0, -- KES amount allocated
    current_balance DECIMAL(15,2) DEFAULT 0, -- Current KES balance in pool
    entry_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    participation_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, pool_id),
    INDEX idx_user_pools (user_id, is_active),
    INDEX idx_pool_participants (pool_id, developer_id)
);

-- Settlement Addresses
CREATE TABLE settlement_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id UUID REFERENCES users(id),
    to_user_id UUID REFERENCES users(id),
    settlement_type VARCHAR(30) NOT NULL, -- 'pool_deposit', 'profit_distribution', 'withdrawal'
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KES',
    amount DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    pool_id UUID,
    reference_id VARCHAR(100),
    settlement_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_settlement_status (status, created_at),
    INDEX idx_user_settlements (from_user_id, to_user_id),
    INDEX idx_pool_settlements (pool_id, settlement_type)
);

-- Address Activity Log
CREATE TABLE address_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    address_id UUID, -- Can reference any address table
    address_value VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2),
    currency VARCHAR(10),
    pool_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_address_activity (address_value, created_at),
    INDEX idx_user_activity (user_id, created_at)
);
```

#### 5.2 API Endpoints

**Regular User Wallet Management:**
```
GET    /api/v1/wallet/regular/addresses      - List user's M-Pesa and pool addresses
POST   /api/v1/wallet/regular/mpesa         - Add/update M-Pesa address
GET    /api/v1/wallet/regular/balance       - Get KES balance across all pools
GET    /api/v1/wallet/regular/pools         - List pool participations
POST   /api/v1/wallet/regular/pools/{pool_id}/join - Join a developer's pool
DELETE /api/v1/wallet/regular/pools/{pool_id} - Leave a pool
```

**Developer Wallet Management:**
```
POST   /api/v1/wallet/developer/exchanges    - Add exchange account
GET    /api/v1/wallet/developer/exchanges    - List exchange accounts
PUT    /api/v1/wallet/developer/exchanges/{id} - Update exchange account
POST   /api/v1/wallet/developer/mpesa       - Set M-Pesa settlement address
GET    /api/v1/wallet/developer/pools       - List managed pools and their addresses
```

**Exchange Address Management (Developers):**
```
POST   /api/v1/wallet/addresses/exchange     - Fetch new exchange deposit address
GET    /api/v1/wallet/addresses/exchange     - List exchange addresses
PUT    /api/v1/wallet/addresses/exchange/{id} - Update exchange address metadata
POST   /api/v1/wallet/addresses/sync         - Sync addresses from exchanges
```

**Pool Address Management:**
```
POST   /api/v1/wallet/pools/{pool_id}/addresses - Create pool-specific addresses
GET    /api/v1/wallet/pools/{pool_id}/addresses - List pool addresses
GET    /api/v1/wallet/pools/{pool_id}/participants - List participant addresses
PUT    /api/v1/wallet/pools/{pool_id}/settlement - Update settlement addresses
```

**Settlement Coordination:**
```
POST   /api/v1/wallet/settlements            - Create settlement request
GET    /api/v1/wallet/settlements            - List user's settlements
GET    /api/v1/wallet/settlements/{id}       - Get settlement details
PUT    /api/v1/wallet/settlements/{id}/confirm - Confirm settlement completion
```

#### 5.3 Address Management Service Architecture

```javascript
class HybridWalletManager {
  constructor() {
    this.regularUserService = new RegularUserWalletService();
    this.developerWalletService = new DeveloperWalletService();
    this.poolAddressService = new PoolAddressService();
    this.settlementService = new SettlementAddressService();
  }

  async createUserWallet(userId, userType) {
    if (userType === 'regular') {
      return await this.regularUserService.createWallet(userId);
    } else if (userType === 'developer') {
      return await this.developerWalletService.createWallet(userId);
    }
  }

  async getAddressesForUser(userId, userType) {
    const baseAddresses = await this.getUserAddresses(userId);
    
    if (userType === 'regular') {
      const poolAddresses = await this.poolAddressService.getUserPoolAddresses(userId);
      return { ...baseAddresses, pools: poolAddresses };
    } else {
      const exchangeAddresses = await this.developerWalletService.getExchangeAddresses(userId);
      const managedPools = await this.poolAddressService.getDeveloperPoolAddresses(userId);
      return { ...baseAddresses, exchanges: exchangeAddresses, pools: managedPools };
    }
  }
}

// Regular User Wallet Service
class RegularUserWalletService {
  async createWallet(userId) {
    // Create primary M-Pesa address entry
    const mpesaAddress = await this.createMpesaAddress(userId, 'mpesa_primary');
    
    // Create tracking addresses for pool participation
    const trackingAddress = await this.createTrackingAddress(userId);
    
    return {
      mpesa: mpesaAddress,
      tracking: trackingAddress,
      balance: 0,
      currency: 'KES'
    };
  }

  async joinPool(userId, poolId, mpesaAddress, amount) {
    // Create pool participation address
    const poolAddress = await this.createPoolParticipationAddress(
      userId, poolId, mpesaAddress, amount
    );
    
    // Create settlement request
    await this.settlementService.createPoolDeposit(
      userId, poolId, mpesaAddress, amount
    );
    
    return poolAddress;
  }
}

// Developer Wallet Service  
class DeveloperWalletService {
  async createWallet(userId) {
    // Create M-Pesa settlement address
    const settlementAddress = await this.createMpesaAddress(userId, 'mpesa_settlement');
    
    return {
      mpesa_settlement: settlementAddress,
      exchanges: [],
      pools: []
    };
  }

  async addExchangeAccount(userId, exchangeConfig) {
    // Create exchange account with encrypted credentials
    const account = await this.createExchangeAccount(userId, exchangeConfig);
    
    // Sync deposit addresses via CCXT
    await this.syncExchangeAddresses(account.id);
    
    return account;
  }

  async syncExchangeAddresses(exchangeAccountId) {
    const account = await this.getExchangeAccount(exchangeAccountId);
    const client = await this.createCCXTClient(account);
    
    const currencies = ['BTC', 'ETH', 'USDT', 'BNB']; // Configurable
    
    for (const currency of currencies) {
      try {
        const address = await client.fetchDepositAddress(currency);
        await this.upsertExchangeAddress(exchangeAccountId, currency, address);
      } catch (error) {
        console.error(`Failed to sync ${currency} address:`, error);
      }
    }
  }
}
```

### 6. M-Pesa Integration Points

#### 6.1 Address Format Validation
```javascript
// M-Pesa address validation (Kenyan phone numbers)
const MPESA_PATTERNS = {
  safaricom: /^(254|0)(7[0-9]{8}|1[0-9]{8})$/,
  formats: [
    '254XXXXXXXXX',  // International format
    '07XXXXXXXX',    // Local format
    '01XXXXXXXX'     // Landline format
  ]
};

function validateMpesaAddress(phoneNumber) {
  return MPESA_PATTERNS.safaricom.test(phoneNumber);
}

function normalizeMpesaAddress(phoneNumber) {
  // Convert to international format (254XXXXXXXXX)
  if (phoneNumber.startsWith('0')) {
    return '254' + phoneNumber.substring(1);
  }
  return phoneNumber;
}
```

#### 6.2 Settlement Flow Management
```javascript
class SettlementAddressService {
  async createPoolDeposit(userId, poolId, mpesaFrom, amount) {
    const developer = await this.getPoolDeveloper(poolId);
    const poolSettlementAddress = await this.getPoolSettlementAddress(poolId);
    
    return await this.createSettlement({
      from_user_id: userId,
      to_user_id: developer.id,
      settlement_type: 'pool_deposit',
      from_address: mpesaFrom,
      to_address: poolSettlementAddress,
      amount: amount,
      currency: 'KES',
      pool_id: poolId
    });
  }

  async createProfitDistribution(poolId, distributions) {
    const settlements = [];
    
    for (const distribution of distributions) {
      const settlement = await this.createSettlement({
        from_user_id: distribution.developerId,
        to_user_id: distribution.userId,
        settlement_type: 'profit_distribution',
        from_address: distribution.developerMpesa,
        to_address: distribution.userMpesa,
        amount: distribution.profitAmount,
        currency: 'KES',
        pool_id: poolId
      });
      
      settlements.push(settlement);
    }
    
    return settlements;
  }
}
```

### 7. Security Considerations

#### 7.1 Multi-User Fund Isolation
- Strict separation between regular user and developer addresses
- Pool-specific address isolation to prevent cross-contamination
- Encrypted storage of developer exchange API credentials
- M-Pesa address validation and normalization
- Settlement address verification before fund transfers

#### 7.2 Financial Security
- Audit trail for all address creation and modifications
- Settlement confirmation requirements
- Pool balance reconciliation checks
- Developer exchange account permission validation
- Rate limiting for sensitive operations

### 8. Performance Requirements

- M-Pesa address validation: < 50ms
- Pool participation: < 1s response time
- Exchange address sync: < 30s per exchange
- Settlement creation: < 200ms
- Address listing: < 150ms (paginated)
- Pool balance queries: < 100ms

### 9. Integration Points

#### 9.1 Internal Dependencies
- **Identity Module:** User authentication and role validation
- **Payments Module:** M-Pesa API integration for actual transactions
- **Trading Engine:** Pool strategy execution and performance tracking
- **Settlements Module:** Profit calculation and distribution logic
- **Notification Service:** Settlement confirmations and pool updates

#### 9.2 External Services
- **M-Pesa API:** Payment processing and verification
- **CCXT Library:** Exchange integration for developers
- **Exchange APIs:** Deposit address management
- **Encryption Services:** API credential protection
- **SMS Services:** M-Pesa transaction confirmations

### 10. Future Enhancements

- Multi-currency support beyond KES
- Advanced pool management features
- Automated settlement scheduling
- Integration with additional Kenyan payment providers
- Enhanced developer analytics and reporting
- Mobile money integration beyond M-Pesa
- Cross-border settlement capabilities

### 11. Testing Strategy

#### 11.1 Unit Tests
- M-Pesa address validation and normalization
- Pool participation logic
- Exchange address synchronization
- Settlement creation and tracking
- User type-specific wallet operations

#### 11.2 Integration Tests
- End-to-end pool joining flow
- Developer exchange account setup
- Settlement coordination between users
- M-Pesa address verification
- Multi-user isolation verification

#### 11.3 Financial Tests
- Pool balance reconciliation
- Settlement amount calculations
- Cross-user fund isolation
- Exchange address security
- Audit trail completeness
