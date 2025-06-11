# Feature Overview

This page details the major features of the copy-trading webhook platform grouped by module.

## Identity
- **Token management** – Issue and revoke API tokens with TTL support.
- **KYC verification** – Accept document uploads and allow admin approval.

## Wallet
- **Address CRUD** – Add, list, update, and delete deposit addresses.

## Marketplace
- **Strategy catalog** – Paginated list of master strategies with search.
- **Strategy management** – Masters can create, update, or remove their strategies.

## Subscription
- **Strategy subscriptions** – Followers subscribe or unsubscribe from strategies.

## Execution
- **Order replication** – Celery workers place follower trades asynchronously and retry on failure.

## Ledger
- **Trade logging** – Record executed orders and expose history with CSV/JSON export.

## Risk
- **Risk limits** – Configure per-user limits and reject orders exceeding them.

## Dashboard
- **Metrics** – Prometheus endpoint with latency and order counters displayed on a simple dashboard or Grafana.

## Compliance
- **Audit logs** – Track token issuance and nonce usage with cleanup and export options.

