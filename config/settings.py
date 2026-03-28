from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "django_filters",
    "apps.core",
    "apps.customers",
    "apps.services_app",
    "apps.billing",
    "apps.integrations",
    "apps.client_portal",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestAuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.system_context",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "qvatel_billing"),
        "USER": os.getenv("POSTGRES_USER", "qvatel"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "qvatel"),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Havana")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", str(60 * 60 * 8)))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "qvatel-billing-cache",
    }
}

AUTH_RATE_LIMIT_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_ATTEMPTS", "5"))
AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "900"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
CELERY_BEAT_SCHEDULE = {
    "generate-monthly-invoices": {
        "task": "apps.billing.tasks.generate_monthly_invoices_task",
        "schedule": 60 * 60 * 24,
    },
    "mark-overdue-invoices": {
        "task": "apps.billing.tasks.mark_overdue_invoices_task",
        "schedule": 60 * 60,
    },
    "send-payment-reminders": {
        "task": "apps.billing.tasks.send_due_reminders_task",
        "schedule": 60 * 60 * 6,
    },
    "auto-suspend-overdue-customers": {
        "task": "apps.billing.tasks.auto_suspend_overdue_customers_task",
        "schedule": 60 * 60 * 12,
    },
}

OPENCLAW_BASE_URL = os.getenv("OPENCLAW_BASE_URL", "https://openclaw.local/api")
OPENCLAW_API_KEY = os.getenv("OPENCLAW_API_KEY", "replace-me")
OPENCLAW_TIMEOUT = int(os.getenv("OPENCLAW_TIMEOUT", "15"))
OPENCLAW_SIMULATION_MODE = os.getenv("OPENCLAW_SIMULATION_MODE", "true").lower() == "true"
OPENCLAW_RETRY_ATTEMPTS = int(os.getenv("OPENCLAW_RETRY_ATTEMPTS", "3"))

SYSTEM_DEFAULT_CURRENCY = os.getenv("SYSTEM_DEFAULT_CURRENCY", "USD")
COMPANY_NAME = os.getenv("COMPANY_NAME", "QvaTel")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
}
