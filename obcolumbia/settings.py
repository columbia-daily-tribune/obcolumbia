"""
Basic settings for OpenBlock.
 
See settings_default.py for additional settings.
"""

from ebpub.settings_default import *

PROJECT_DIR = os.path.normpath(os.path.dirname(__file__))
INSTALLED_APPS = ('obcolumbia','olwidget',) + INSTALLED_APPS 
TEMPLATE_DIRS = (os.path.join(PROJECT_DIR, 'templates'), ) + TEMPLATE_DIRS
ROOT_URLCONF = 'obcolumbia.urls'

ADMIN_MEDIA_PREFIX = "/media/"
MAP_ICONS_PATH = os.path.normpath(os.path.join(os.path.dirname(PROJECT_DIR), 'map_icons'))

########################
# CORE DJANGO SETTINGS #
########################

DEBUG = True

# Multi-database configuration as per
# http://docs.djangoproject.com/en/1.2/topics/db/multi-db/

DATABASES = {
    'default': {
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'OPTIONS': {},
        'HOST': '',
        'PORT': '',
        'TEST_NAME': 'test_openblock'
    },
}

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
    )

#########################
# CUSTOM EBPUB SETTINGS #
#########################

# The domain for your site.
EB_DOMAIN = 'localhost'

# This is the short name for your city, e.g. "chicago".
SHORT_NAME = 'columbia'

# Set both of these to distinct, secret strings that include two instances
# of '%s' each. Example: 'j8#%s%s' -- but don't use that, because it's not
# secret.  And don't check the result in to a public code repository
# or otherwise put it out in the open!
PASSWORD_CREATE_SALT = 'change this too'
PASSWORD_RESET_SALT = 'change this'

# You probably don't need to override this, the setting in settings.py
# should work out of the box.
#EB_MEDIA_ROOT = '' # necessary for static media versioning.

EB_MEDIA_URL = '' # leave at '' for development

# Map.
MAP_BASELAYER_TYPE = 'cloudmade.998'
# You need to override this in your settings_local file.
CLOUDMADE_API_KEY='FIX ME'

# This is used as a "From:" in e-mails sent to users.
GENERIC_EMAIL_SENDER = 'openblock@' + EB_DOMAIN

# Filesystem location of scraper log.
SCRAPER_LOGFILE_NAME = '/tmp/scraperlog'

# If this cookie is set with the given value, then the site will give the user
# staff privileges (including the ability to view non-public schemas).
STAFF_COOKIE_NAME = 'obstaff'
STAFF_COOKIE_VALUE = 'makethissomevalue'

# What kinds of news to show on the homepage.
HOMEPAGE_DEFAULT_NEWSTYPES = [u'news-articles']

# How many days of news to show on the homepage & elsewhere.
DEFAULT_DAYS = 30

# And how many items maximum.
# Note used twice - once for news, once for events.
MAX_HOMEPAGE_ITEMS = 5

# Where to center citywide  maps, eg. on homepage.
DEFAULT_MAP_CENTER_LON = -92.33399
DEFAULT_MAP_CENTER_LAT = 38.95177
DEFAULT_MAP_ZOOM = 12

# Metros.
METRO_LIST = (
    {
        # Extent of the metro, as a longitude/latitude bounding box.
        'extent': (-92.565644, 38.790055, -92.047137, 39.13438),

        # Whether this should be displayed to the public.
        'is_public': True,

        # Set this to True if the metro has multiple cities.
        'multiple_cities': False,

        # The major city in the metro.
        'city_name': 'Columbia',

        # The SHORT_NAME in the settings file (also the subdomain).
        'short_name': 'columbia',

        # The name of the metro, as opposed to the city (e.g., "Miami-Dade" instead of "Miami").
        'metro_name': 'Columbia',

        # USPS abbreviation for the state.
        'state': 'MO',

        # Full name of state.
        'state_name': 'Missouri',

        # Time zone, as required by Django's TIME_ZONE setting.
        'time_zone': 'America/Chicago',
    },
)

if DEBUG:
    for _name in required_settings:
        if not _name in globals():
            raise NameError("Required setting %r was not defined in settings.py or default_settings.py" % _name)

# Columbia doesn't have "neighborhoods."
DEFAULT_LOCTYPE_SLUG = 'wards'


######################################################
# API keys for scrapers
FLICKR_API_KEY = 'fix me'
FLICKR_API_SECRET = 'fix me'
MEETUP_API_KEY = 'fix me'

DJANGO_STATIC = not DEBUG

# Select your login view API.
# Choices are 'ebpub.db.views:login', 'obcolumbia.views:blox_login', 'obcolumbia.views:oauth_login'

LOGIN_VIEW = 'ebpub.db.views:login'

##############################################################
# Ellington OAuth configuration.
#
# After how many seconds should we attempt to refresh the auth token?
# Too high and we risk not knowing when a user's subscription has
# expired or account closed; too low and we'll hurt performance by
# making unnecessary requests to the oauth provider.
OAUTH_REFRESH_TIMEOUT = 60 * 10

OAUTH_CONSUMER_KEY = 'openblock'
OAUTH_CONSUMER_SECRET = 'secret'
OAUTH_REQUEST_TOKEN_URL = 'http://localhost:8700/oauth/request_token/'
OAUTH_ACCESS_TOKEN_URL = 'http://localhost:8700/oauth/access_token/'
OAUTH_AUTHORIZE_URL = 'http://localhost:8700/oauth/authorize/'
OAUTH_SCOPE="subscriber_info"

# This is not part of the OAuth protocol; we need Ellington to provide it.
OAUTH_USER_INFO_URL = 'http://localhost:8700/subscriber-info/'

# Session cookies cannot use the same domain & cookie name as
# ellington, or else they clash and we can't log in.  Since we'll
# probably be using the same domain name, change the cookie name.
SESSION_COOKIE_NAME='obcolumbia_session'

# Finally, this middleware periodically checks the oauth provider to
# make sure we don't have stale account info.
MIDDLEWARE_CLASSES += (
    'obcolumbia.middleware.OauthRefreshMiddleware',
    )

# Hook from ebpub.db that allows us to override the Schemas that are
# allowed in NewsItem queries, on a per-user basis.
SCHEMA_MANAGER_HOOK = 'obcolumbia.utils:schema_manager_filter'

# Hook from ebpub.neighbornews that determines whether the
# NeighborNews add forms require a CAPTCHA.
NEIGHBORNEWS_USE_CAPTCHA = 'obcolumbia.utils:neighbornews_use_captcha'

LOGGING['loggers']['obcolumbia'] = {
    'handlers': [],
    'propagate': True,
    'level':'INFO',
    }

if DEBUG:
    LOGGING['loggers']['obcolumbia']['level'] = 'DEBUG'
    LOGGING['loggers']['obcolumbia']['handlers'] = ['console']
    LOGGING['handlers']['console']['level'] = 'DEBUG'

# We add context processors for stuff to existing ones from settings_default.py
TEMPLATE_CONTEXT_PROCESSORS += (
    'obcolumbia.context_processors.allowed_location_types',
	'obcolumbia.context_processors.allowed_schemas',
	'obcolumbia.context_processors.todays_date',
	'obcolumbia.context_processors.street_count',
    'obcolumbia.context_processors.allowed_locations',
)

###############################################################################
# Local settings go last.
LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'settings_local.py')
if os.path.exists(LOCAL_SETTINGS_FILE):
    execfile(LOCAL_SETTINGS_FILE)

