"""Isolated manual AI profile; production PostgreSQL settings stay unchanged."""
from .settings import *

LAD_AI_RUNTIME = Path(os.environ.get('LAD_AI_RUNTIME', BASE_DIR.parent / '.runtime' / 'i02')).resolve()
LAD_AI_RUNTIME.mkdir(parents=True, exist_ok=True)
if os.environ.get('LAD_AI_TEST') == '1':
    SECRET_KEY = 'isolated-integration-tests-only-not-a-deployment-key'
else:
    SECRET_KEY = (LAD_AI_RUNTIME / 'django-secret.txt').read_text(encoding='utf-8').strip()
DEBUG = False
# Avoid autodiscover of document/RAG admin modules in this minimal profile.
INSTALLED_APPS = ['django.contrib.admin.apps.SimpleAdminConfig' if app == 'django.contrib.admin' else app for app in INSTALLED_APPS]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': LAD_AI_RUNTIME / 'django.sqlite3', 'OPTIONS': {'timeout': 10}}}
ROOT_URLCONF = 'config.ai_local_urls'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
LAD_AI_MAPPING = LAD_AI_RUNTIME / 'mapping.json'
LAD_AI_SECRET_FILE = LAD_AI_RUNTIME / 'ipc-secret.txt'
LAD_AI_PORT = int(os.environ.get('LAD_AI_PORT', '8372'))
LAD_FRONTEND_PORT = int(os.environ.get('LAD_FRONTEND_PORT', '5173'))
CORS_ALLOWED_ORIGINS = [f'http://{host}:{LAD_FRONTEND_PORT}' for host in ('localhost', '127.0.0.1')]
MEDIA_ROOT = LAD_AI_RUNTIME / 'private-media'
LAD_AI_AUTOGRADE = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 49152
PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']

# Third-party parser diagnostics can contain input data.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'ignore_pdf_diagnostics': {'class': 'logging.NullHandler'}},
    'loggers': {'pypdf': {'handlers': ['ignore_pdf_diagnostics'], 'propagate': False}},
}