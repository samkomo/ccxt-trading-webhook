# Execution Module

Replicates master orders on follower accounts using Celery workers.

- **Order replication** – Celery workers place follower trades asynchronously and retry on failure.
