# Feature Overview

This page details the major features of the copy-trading webhook platform. The codebase is organised into domain packages under `app/` which map to these features.

## Identity (`app.identity`)
- **Token management** – Issue and revoke API tokens with TTL support.
- **KYC verification** – Accept document uploads and allow admin approval.

## Wallet (`app.wallet`)
- **Address CRUD** – Add, list, update, and delete deposit addresses.

## Marketplace (`app.marketplace`)
- **Strategy catalog** – Paginated list of master strategies with search.
- **Strategy management** – Masters can create, update, or remove their strategies.

## Subscription (`app.subscription`)
- **Strategy subscriptions** – Followers subscribe or unsubscribe from strategies.

## Execution (`app.execution`)
- **Order replication** – Celery workers place follower trades asynchronously and retry on failure.

## Ledger (`app.ledger`)
- **Trade logging** – Record executed orders and expose history with CSV/JSON export.

## Risk (`app.risk`)
- **Risk limits** – Configure per-user limits and reject orders exceeding them.

## Dashboard (`app.dashboard`)
- **Metrics** – Prometheus endpoint with latency and order counters displayed on a simple dashboard or Grafana.

## Compliance (`app.compliance`)
- **Audit logs** – Track token issuance and nonce usage with cleanup and export options.

