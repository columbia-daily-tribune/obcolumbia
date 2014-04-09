Columbia Openblock Django App
=============================

Columbia's openblock instance is a custom django project as described
in the `Custom Site` documentation of openblock.  These instructions
describe how to install the application from scratch.  To upgrade an
existing installation, see the "Upgrade" documentation below.

Make you have access to the custom project on github at
https://github.com/openplans/obcolumbia before you start.


Quickstart Instructions for Ubuntu 11.04
========================================

These instructions apply to Ubuntu 11.04 Server.  Please see the
general Openblock documentation at http://openblockproject.org/docs/
for troubleshooting and other information.


Install System Packages
-----------------------

These ubuntu packages cover the basic openblock system requirements::

    $ sudo apt-get install \
        build-essential \
        git-core \
        libproj-dev \
        libproj0 \
        postgresql-8.4-postgis \
        postgresql-server-dev-8.4 \
        python-distribute  \
        python-gdal \
        python-lxml \
        python-virtualenv \
        python2.7 \
        python2.7-dev \
        subversion \
        unzip \
        wget

    $ sudo ldconfig


Configure Postgres Authentication
---------------------------------

Edit **/etc/postgresql/8.4/main/pg_hba.conf** to allow all local users
unlimited access to the database.  Remove or comment out the line
reading::

    local all all ident 

Replace it with a line reading::

    local all all trust

... and restart postgres::

    $ sudo favorite_editor /etc/postgresql/8.4/main/pg_hba.conf
    $ sudo /etc/init.d/postgresql restart


Setup Database Template and Openblock User
------------------------------------------

These steps set up the database template and database user for
openblock.  They are performed as the postgres user. You only need to
do this once per database server::

    $ sudo su - postgres
    $ createdb -E UTF8 template_postgis
    $ createlang -d template_postgis plpgsql
    $ psql -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis';"
    $ psql -d template_postgis -f /usr/share/postgresql/8.4/contrib/postgis-1.5/postgis.sql
    $ psql -d template_postgis -f /usr/share/postgresql/8.4/contrib/postgis-1.5/spatial_ref_sys.sql
    $ psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;"
    $ psql -d template_postgis -c "GRANT ALL ON geography_columns TO PUBLIC;"
    $ psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

    $ createuser --createdb openblock
    $ exit

Install Openblock Software
--------------------------

These steps are performed as the user that openblock will run as::

    $ virtualenv openblock
    $ cd openblock 
    $ source bin/activate 

    $ easy_install pip 
    $ hash -r 
    $ easy_install --upgrade distribute

    $ mkdir -p src
    $ git clone git://github.com/openplans/openblock.git src/openblock
    $ git clone https://TribuneSupport@github.com/openplans/obcolumbia.git src/obcolumbia

    $ pip install -r src/openblock/ebpub/requirements.txt 
    $ pip install -e src/openblock/ebpub
    $ pip install -r src/openblock/ebdata/requirements.txt 
    $ pip install -e src/openblock/ebdata
    $ pip install -r src/openblock/obadmin/requirements.txt 
    $ pip install -e src/openblock/obadmin
    $ pip install -e src/obcolumbia

Next we initialize the database.  Here we assume that you're using the
default database configuration on localhost.  If you override the
database config with local settings (see below), you may need to
adjust this command::

    $ createdb -U openblock -T template_postgis openblock_obcolumbia 

    $ export DJANGO_SETTINGS_MODULE=obcolumbia.settings
    $ django-admin.py syncdb --migrate


This completes the basic setup.  The next task is to load data and
start the openblock services.

Custom Local Settings
=====================

*Highly* recommended: An optional ``settings_local.py`` may be placed
alongside the ``src/obcolumbia/settings.py`` file, to add local
settings overrides.  These will not be affected by git pull.
You should add this file to whatever backup system you use.

Some things you might like to override: change the DATABASES setting
for an offbox database, or enable and configure OAuth login, etc.

Settings you must override in settings_local.py
-----------------------------------------------

CLOUDMADE_API_KEY: Needed for our default map base layer.
Register at http://cloudmade.com/ and get an API key.

MEETUP_API_KEY:  Needed for the Meetups scraper. See http://www.meetup.com/meetup_api/key/

FLICKR_API_KEY, FLICKR_API_SECRET: Needed for the Flickr scraper. See
https://secure.flickr.com/services/apps/create/apply
(I'm guessing that the Tribune qualifies for "non-commercial".)

RECAPTCHA_PUBLIC_KEY, RECAPTCHA_PRIVATE_KEY: Needed for
user-contributed content. See https://www.google.com/recaptcha/admin/create

See also the Oauth section below.


Loading Data
============

Make sure that you have successfully created the databases for the
obcolumbia site as configured in ``src/obcolumbia/obcolumbia/settings_local.py``
and followed the instructions for syncing and setting up the database
in the custom app deployment documentation.

From the root of your environment::

    $ source bin/activate
    $ export DJANGO_SETTINGS_MODULE=obcolumbia.settings

Create columbia schemas::

    $ django-admin.py loaddata src/obcolumbia/obcolumbia/fixtures/obcolumbia_schemas.json

Load columbia locations::

    $ django-admin.py loaddata src/obcolumbia/obcolumbia/fixtures/obcolumbia_locations.json

Load columbia street address data (takes a while)::

    $ src/obcolumbia/data/import_columbia_blocks.sh

Note that Places are not loaded at this point, those get created by
the "businesses" scraper, see the "Running Scrapers" section below.


Creating an Admin User
======================

To use the admin UI, you'll need a user with admin privileges.  One
should have been created during the initial "manage.py syncdb", but if
not, or if you've forgotten the credentials, you can always create a
new one by doing this::

  cd /path/to/your/virtualenv
  source bin/activate
  DJANGO_SETTINGS_MODULE=obcolumbia.settings django-admin.py createsuperuser

If OAuth login is enabled (see below), you'll need to use a special
URL to log in with this superuser, or any other account that uses a
password instead of OAuth. The URL is ``/accounts/password_login/``.
(The password-based login form should also be used automatically
if you try to visit the /admin UI when logged out.)


Configuring Authentication
============================

Note that settings.USE_OAUTH_LOGIN is no longer used!
Instead, we now use settings.LOGIN_VIEW as described below,
since there are multiple possible authentication sources.


Default password-based registration / login
--------------------------------------------

If settings.LOGIN_VIEW is not set, or is set to
'ebpub.accounts.views:login', then login will be via the usual
OpenBlock form where users can enter an email address and password.

OAuth integration (Ellington)
------------------------------


If settings.LOGIN_VIEW is set to 'obcolumbia.views:oauth_login', the
normal Openblock login screens will be replaced with ones that
redirect to an OAuth provider for approval.

**Note this is only tested with Ellington**. Other OAuth providers
have not been tested.

You also **must** set OAUTH_CONSUMER_KEY and OAUTH_CONSUMER_SECRET
to values that Ellington must provide.

Several OAuth URLs **must** also be configured in your settings file.
These are:

OAUTH_REQUEST_TOKEN_URL
OAUTH_ACCESS_TOKEN_URL
OAUTH_AUTHORIZE_URL
OAUTH_USER_INFO_URL

Ask your Ellington contact for suitable values for these settings.

OAUTH_SCOPE should be set to "subscriber_info" for use with Ellington.

Once this is all set up, the logged-in user's subscriber status will
be re-checked from Ellington every so often, to ensure that eg. a user
whose subscription has expired can't stay logged in to Openblock
indefinitely. By default, this is checked every 10 minutes.  To change
how often this is checked, change settings.OAUTH_REFRESH_TIMEOUT.

OAuth integration (Other providers)
-----------------------------------

The 'obcolumbia.views:oauth_login' view *might* work with other OAuth
providers aside from Ellington, but this is completely untested!
The code most likely would need modifications in that case.
For example, the OAUTH_USER_INFO_URL is specific to Ellington and is
not part of the OAuth protocol; you'd probably need to modify the code
to get subscriber info from the OAuth provider.


TownNews BLOX CMS authentication
--------------------------------

If settings.LOGIN_VIEW is set to 'obcolumbia.views:blox_login', the
normal Openblock login screens will be replaced with ones that
redirect to a Blox TownNews site for login.

Several Blox-specific settings must also be configured in the blox
section of obcolumbia/settings.py (or settings_local.py). These are:

BLOX_PROVIDER_URL - the base URL of the BLOX site.
BLOX_API_KEY - ask your TownNews contact for this.
BLOX_API_SECRET - ask your TownNews contact for this.


Custom authentication
---------------------

It should be straightforward to integrate other authentication systems
by writing a new ``login(request)`` function. Use the existing
examples in ``views.py`` as examples.

(We haven't written a Django `auth backend
<https://docs.djangoproject.com/en/1.3/topics/auth/#authentication-backends>`_
for either Ellington or TownNews, because the Django auth backend API
didn't look like a great match for a federated login approach, like
OAuth, which spans multiple requests.  Doing it via view functions
instead was simple and expedient.)


Deploying
=========

The ``src/obcolumbia/etc`` folder contains example configuration for
obcolumbia.

If you are deploying using Apache and mod_wsgi, you can use the included
``src/obcolumbia/etc/obcolumbia.wsgi``.

An example Apache virtual host configuration (used for
columbia.openblock.org) is included for reference in
``src/obcolumbia/etc/columbia.openblock.org``.
Copy this to your Apache configuration directory and adjust paths and
hostnames as needed.

Running Scrapers
=================

To run scrapers periodically, you can use ``cron``.
An example crontab file is provided at ``src/obcolumbia/etc/sample_crontab``.
You can copy this to /etc/cron.d/ and adjust paths as needed.
Also, if you are running openblock as a different user than
``openblock``, you will want to update the sixth column of the crontab.

Also be sure to update the MAILTO address, so email can be sent to
this user on errors.

In case of problems, you should then get error email. If you don't,
have a look at ``/var/log/syslog``, which should have output from
cron; and/or the file pointed to by settings.SCRAPER_LOGFILE_NAME,
which should have more verbose output from the scraper scripts
themselves.

NOTE: Previous versions of this document described setting up
``updaterdaemon`` to periodically run scrapers. It has been deprecated
in favor of ``cron``.

Upgrading
=========

From the root of your environment::

    $ cd path/to/openblock
    $ source bin/activate
    $ export DJANGO_SETTINGS_MODULE=obcolumbia.settings

Upgrade the openblock source code::

    $ cd $VIRTUAL_ENV/src/openblock
    $ git pull
    $ pip install -r ebpub/requirements.txt
    $ pip install -e ebpub
    $ pip install -r ebdata/requirements.txt
    $ pip install -e ebdata
    $ pip install -r obadmin/requirements.txt
    $ pip install -e obadmin

Upgrade the obcolumbia source code::

    $ cd $VIRTUAL_ENV/src/obcolumbia
    $ git pull
    $ pip install -e .

Run any OpenBlock core database migrations that are pending::

    $ django-admin.py syncdb
    $ django-admin.py migrate db
    $ django-admin.py migrate streets

Re-load the columbia data types::

    $ django-admin.py loaddata $VIRTUAL_ENV/src/obcolumbia/obcolumbia/fixtures/obcolumbia_schemas.json
    $ django-admin.py loaddata $VIRTUAL_ENV/src/obcolumbia/obcolumbia/fixtures/obcolumbia_tags.json

Run any remaining database migrations, eg columbia-specific ones::

    $ django-admin.py syncdb --migrate

After this the website can be restarted.

