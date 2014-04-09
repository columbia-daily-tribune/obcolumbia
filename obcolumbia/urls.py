from django.conf.urls.defaults import *
from django.conf import settings
from obadmin import admin

admin.autodiscover()

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^map_icons/(?P<path>.*)$',
         'django.views.static.serve', {'document_root': settings.MAP_ICONS_PATH}),
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns(

    '',

    # Override homepage.
    url(r'^$', 'obcolumbia.views.homepage', name='ebpub-homepage'),

    # Override login form to use Oauth.
    url(r'^accounts/login/$', 'obcolumbia.views.login', name='accounts-login'),

    # Provide a new URL to have a way to use password-based login.
    url(r'^accounts/password_login/$', 'ebpub.accounts.views.login',
        kwargs={'override_target': '../password_login/'},
        name='password-login'),

    url(r'^accounts/logout/$', 'obcolumbia.views.logout', name='accounts-logout'),
    url(r'^admin/logout/$', 'obcolumbia.views.logout', name='admin-logout'),

    (r'^admin/', include(admin.site.urls)),

    # ebpub provides all the UI for an openblock site.
    (r'^', include('ebpub.urls')),
)


