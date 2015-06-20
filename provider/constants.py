from datetime import timedelta
from django.conf import settings

CONFIDENTIAL = 0
PUBLIC = 1

CLIENT_TYPES = (
    (CONFIDENTIAL, "Confidential (Web applications)"),
    (PUBLIC, "Public (Native and JS applications)")
)

RESPONSE_TYPE_CHOICES = getattr(settings, 'OAUTH_RESPONSE_TYPE_CHOICES', ("code", "token"))

TOKEN_TYPE = 'Bearer'

READ = 1 << 1
WRITE = 1 << 2
READ_WRITE = READ | WRITE

DEFAULT_SCOPES = (
    (READ, 'read', 'Read your data'),
    (WRITE, 'write', 'Write your data'),
    (READ_WRITE, 'read+write'),
)

SCOPES = getattr(settings, 'OAUTH_SCOPES', DEFAULT_SCOPES)

EXPIRE_DELTA = getattr(settings, 'OAUTH_EXPIRE_DELTA', timedelta(days=365))

# Expiry delta for public clients (which typically have shorter lived tokens)
EXPIRE_DELTA_PUBLIC = getattr(settings, 'OAUTH_EXPIRE_DELTA_PUBLIC', timedelta(days=30))

EXPIRE_CODE_DELTA = getattr(settings, 'OAUTH_EXPIRE_CODE_DELTA', timedelta(seconds=10 * 60))

# Remove expired tokens immediately instead of letting them persist.
DELETE_EXPIRED = getattr(settings, 'OAUTH_DELETE_EXPIRED', False)

ENFORCE_SECURE = getattr(settings, 'OAUTH_ENFORCE_SECURE', False)
ENFORCE_CLIENT_SECURE = getattr(settings, 'OAUTH_ENFORCE_CLIENT_SECURE', True)

SESSION_KEY = getattr(settings, 'OAUTH_SESSION_KEY', 'oauth')

SINGLE_ACCESS_TOKEN = getattr(settings, 'OAUTH_SINGLE_ACCESS_TOKEN', False)

LOGO_FOLDER = getattr(settings, 'OAUTH2_LOGO_FOLDER', 'logos')

IMAGE_STORAGE = getattr(settings, 'OAUTH2_IMAGE_STORAGE', None)

# Limit the number of refresh token for the same client with same scope (0 is unlimit)
LIMIT_NUM_REFRESH_TOKEN = getattr(settings, 'OAUTH_LIMIT_NUM_REFRESH_TOKEN', 0)

# Do not invalidate the refresh token when using the it to refresh access token
KEEP_REFRESH_TOKEN = getattr(settings, 'OAUTH_KEEP_REFRESH_TOKEN', False)
