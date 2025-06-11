# 📂 Sprint Backlog

This backlog is organized using ZenHub's five-level hierarchy: **Initiative → Project → Epic → Issue → Sub‑task**. Story points (1–5) estimate the effort for each issue.

## Initiative: MVP Launch of the Copy-Trading Platform
Deliver a minimal but reliable platform with secure authentication, automated trade replication, monitoring, and compliance features.

### Project: Identity
Manage user identity with token authentication and KYC workflows.

#### Epic: Access Token Management
Secure issuance and revocation of API tokens.

**Issue – Issue & Revoke Tokens (2 pts)**
- [ ] `/token/issue` route calling `token_store.issue_token`
- [ ] `/token/revoke` route calling `token_store.revoke_token`
- [ ] Unit tests for issuance and revocation flows
- [ ] Update API docs with examples

#### Epic: KYC Verification
Collect documents and approve user identity.

**Issue – Submit & Review KYC (3 pts)**
- [ ] Endpoint for document upload
- [ ] Secure storage for uploaded files
- [ ] Save KYC status on user profile
- [ ] Admin interface to approve or reject submissions

### Project: Wallet
Handle deposit and withdrawal addresses per exchange.

#### Epic: Address Management
Allow users to manage their saved addresses.

**Issue – Manage Wallet Addresses (3 pts)**
- [ ] Create address endpoint
- [ ] List addresses endpoint
- [ ] Update address labels
- [ ] Delete address with ownership check
- [ ] Validate address format per chain

### Project: Marketplace
Central hub for discovering master trading strategies.

#### Epic: Strategy Catalog
List strategies with basic search and pagination.

**Issue – List Strategies (3 pts)**
- [ ] Strategy model with metadata fields
- [ ] Paginated list endpoint
- [ ] Search and filter options
- [ ] Unit tests for listing behaviour

#### Epic: Strategy CRUD for Masters
Enable master traders to manage their strategy listings.

**Issue – Manage Strategies (3 pts)**
- [ ] Create strategy endpoint
- [ ] Update strategy endpoint
- [ ] Delete strategy endpoint
- [ ] Permission checks per master
- [ ] Tests covering full CRUD

### Project: Subscription
Manage follower subscriptions to master strategies.

#### Epic: Strategy Subscription
Handle subscription lifecycle and credential checks.

**Issue – Manage Subscriptions (2 pts)**
- [ ] Create subscription endpoint
- [ ] Unsubscribe endpoint
- [ ] Persist subscription state
- [ ] Validate exchange credentials
- [ ] Notify user on subscription change

### Project: Execution
Place follower trades when masters act.

#### Epic: Order Replication
Use Celery workers to execute orders asynchronously.

**Issue – Execute Follower Trades (3 pts)**
- [ ] Worker task `_execute_order` using ccxt
- [ ] Queue incoming orders
- [ ] Retry on temporary errors
- [ ] Log order details on success
- [ ] Unit tests with mocked exchanges

### Project: Ledger
Persistent ledger of all executed trades.

#### Epic: Trade Logging
Store trade data and expose history.

**Issue – Record Executed Trades (3 pts)**
- [ ] Database schema for trade records
- [ ] Write log entry after each execution
- [ ] History API to retrieve trades
- [ ] CSV/JSON export option
- [ ] Tests for persistence

### Project: Risk Management
Enforce per-user limits to control exposure.

#### Epic: Risk Limits
Block trades that exceed configured thresholds.

**Issue – Configure & Enforce Limits (2 pts)**
- [ ] Endpoint to set max size and daily loss
- [ ] Validate orders against limits
- [ ] Alert when limits are breached
- [ ] Unit tests for enforcement logic

### Project: Metrics Dashboard
Expose system metrics for observability.

#### Epic: Metrics & Monitoring
Collect latency and order counts with Prometheus.

**Issue – Monitor Request Latency (2 pts)**
- [ ] `/metrics` endpoint with Prometheus histograms
- [ ] Display latency and order counts on a dashboard
- [ ] Optional Grafana integration
- [ ] Documentation on running the dashboard

### Project: Compliance
Store records to satisfy regulatory needs.

#### Epic: Audit Logs
Persist token and nonce usage with retention.

**Issue – Maintain Audit Records (3 pts)**
- [ ] Persist token and nonce usage logs
- [ ] Scheduled cleanup of expired records
- [ ] Export interface for auditors
- [ ] Tests verifying expiry cleanup

**Total Estimate:** 29 points
