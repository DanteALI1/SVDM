import os
os.environ.setdefault("DJANGO_SECRET_KEY", "smoke-test-secret-key-not-for-prod")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/svdb-smoke.db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
from config.settings import *
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/tmp/svdb-smoke.db"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
ALLOWED_HOSTS = ["*"]
