"""
Django settings for appointment_backend project.
"""

from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Charger le .env ───────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env", encoding='utf-8', override=True)

SECRET_KEY = 'django-insecure-change-this-in-production-use-env-variable'

DEBUG = True

ALLOWED_HOSTS = ['*']

# ── Installed Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',

    # Local — Backend principal
    'users',
    'doctors',
    'patients',
    'pharmacy',
    'caretaker',
    'consultations',
    'appointments',
    'prescriptions',
    'medications',
    'notifications',
    'admin_panel',
    'messaging',
    'settings',

    # ✅ Bot IA Diagnostic
    'diagnostic_ai',
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'medical_db',
        'USER':     'postgres',
        'PASSWORD': 'yassir',
        'HOST':     'localhost',
        'PORT':     '5432',
        'OPTIONS':  {'client_encoding': 'UTF8'},
    },
}

# ── Cache ─────────────────────────────────────────────────────────────────────
# DatabaseCache requis pour le NIH validator du bot IA (partagé entre workers)
# Après migration, lancer : python manage.py createcachetable
CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':      '200/hour',
        'user':      '5000/hour',
        'login':     '5/minute',
        'diagnosis': '50/day',    # ✅ NOUVEAU — limite les diagnostics IA à 5/jour/patient
    }
}

# ── Spectacular (OpenAPI) ─────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE':                'MedSmart API',
    'DESCRIPTION':          'Documentation complète de l\'API MedSmart (PFE).',
    'VERSION':              '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_PATCH':    True,
    'COMPONENT_SPLIT_REQUEST':  True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking':          True,
        'persistAuthorization': True,
        'displayOperationId':   True,
    },
}

# ── Simple JWT ────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True  # dev only

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'Africa/Algiers'
USE_I18N      = True
USE_TZ        = True

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# Taille max upload : 10 MB (pour l'analyse de fichiers médicaux)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.CustomUser'

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND      = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST         = 'smtp.gmail.com'
EMAIL_USE_TLS      = True
EMAIL_PORT         = 587
EMAIL_HOST_USER    = 'medicalsmartapp@gmail.com'
EMAIL_HOST_PASSWORD = 'yarvxitxohgcjkwo'
DEFAULT_FROM_EMAIL = 'medicalsmartapp@gmail.com'

# ══════════════════════════════════════════════════════════════════════════════
# ✅ CONFIG BOT IA & RAG — diagnostic_ai
# ══════════════════════════════════════════════════════════════════════════════

# Clé API Gemini (depuis .env)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL",   "gemini-2.5-flash")

# Chemins dataset — dans le projet (BASE_DIR/chroma_db et BASE_DIR/dataset/processed)
CHROMA_PATH     = str(BASE_DIR / os.getenv("CHROMA_PATH",  "chroma_db"))
DATASET_PATH    = str(BASE_DIR / os.getenv("DATASET_PATH", "dataset/processed"))

# Modèle embedding multilingue
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

# Paramètres RAG
RAG_TOP_K       = int(os.getenv("RAG_TOP_K", "5"))
MAX_HISTORY_LEN = 6

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version':                  1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} — {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'console': {
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level':    'INFO',
    },
    'loggers': {
        'django': {
            'handlers':  ['console'],
            'level':     'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers':  ['console'],
            'level':     'ERROR',
            'propagate': False,
        },
        # ✅ logs du bot IA
        'diagnostic_ai': {
            'handlers':  ['console'],
            'level':     'DEBUG',
            'propagate': False,
        },
        'infrastructure': {
            'handlers':  ['console'],
            'level':     'INFO',
            'propagate': False,
        },
    },
}