web: uvicorn main:app --host=0.0.0.0 --port=${PORT:-5000}
worker: celery -A app.tasks worker --loglevel=info
