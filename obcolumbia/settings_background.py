from obcolumbia.settings import *

# Use this settings file when running `django-admin.py process_tasks`.
# Disables default logging config, because a bug in django-background-task
# means that any existing logging config overrides the command-line options.
# See https://github.com/lilspikey/django-background-task/issues/2

del(LOGGING)
