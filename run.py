from app import create_app

app = create_app()

if __name__ == "__main__":
    # Only for local development; use Gunicorn in production
    app.run(host="0.0.0.0", port=5000)
