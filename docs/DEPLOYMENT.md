# Deployment Guide

This document describes how to deploy the **CCXT FastAPI Webhook** to different environments. In addition to the Heroku instructions in the `README`, this guide covers container-based deployments using Docker Compose and general server deployments.

---

## 1. Deploying to Heroku

The repository already includes a `Procfile` and `runtime.txt` so it is ready for Heroku out of the box.

### CLI Steps

```bash
heroku create ccxt-fastapi-webhook
heroku config:set WEBHOOK_SECRET=<your_secret>
heroku addons:create heroku-redis:hobby-dev
heroku config:set CELERY_BROKER_URL=$(heroku config:get REDIS_URL)
heroku config:set CELERY_RESULT_BACKEND=$(heroku config:get REDIS_URL)
heroku config:set QUEUE_ORDERS=true
# Optional default exchange credentials
heroku config:set DEFAULT_EXCHANGE=binance
heroku config:set DEFAULT_API_KEY=<api_key>
heroku config:set DEFAULT_API_SECRET=<api_secret>

# Deploy
git push heroku main
heroku ps:scale web=1 worker=1
```

### GitHub Deploy
1. Open the **Deploy** tab in your Heroku dashboard.
2. Connect your GitHub repository and enable **Auto Deploy** on `main`.
3. Define the same environment variables under **Config Vars**.
4. Provision Redis and scale both the `web` and `worker` dynos.

---

## 2. Deploying with Docker Compose

A `Dockerfile` and sample `docker-compose.yml` are provided. These allow you to run the webhook, a Celery worker and Redis in containers.

### Build and Run

```bash
# Build the image
docker compose build

# Start services in the background
docker compose up -d
```

The webhook will be available on port `8000` and Redis is used for Celery message passing.

---

## 3. Running on a VPS

For a traditional virtual machine or bare-metal server:

1. Install Python 3.10, Redis, and a process manager such as **systemd**.
2. Clone the repository and install dependencies from `requirements.txt`.
3. Configure the environment variables in `/etc/ccxt-webhook.env` or a similar location.
4. Serve the application behind **Nginx** or enable TLS directly with Uvicorn as shown in the README.
5. Create systemd units for both the web process and the Celery worker so they start on boot.

This approach mirrors the Heroku setup but gives you full control over the underlying server.

---

## 4. Environment Variables

Make sure to provide at least the following variables in any deployment:

- `WEBHOOK_SECRET` – shared secret for authentication
- `DEFAULT_EXCHANGE` – fallback exchange name
- `CELERY_BROKER_URL` – broker URL, e.g. `redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND` – result backend URL
- `QUEUE_ORDERS` – set to `true` to enable Celery

Optional values such as `DEFAULT_API_KEY` and `DEFAULT_API_SECRET` can also be configured if you want a fallback key/secret.

