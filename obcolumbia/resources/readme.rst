This folder is served by Apache. It contains our static file additions, to avoid django.contrib.staticfiles.
Rather than do that, we've elected to use a bunch of aliases.

contents of /etc/apache2/site-enabled/cleanob:

Alias /media/ /home/twilliams/cleanob/lib/python2.7/site-packages/django/contrib/admin/media/
Alias /static/admin/ /home/twilliams/cleanob/lib/python2.7/site-packages/django/contrib/admin/media/
Alias /styles/ /home/twilliams/cleanob/src/openblock/ebpub/ebpub/media/styles/
Alias /scripts/ /home/twilliams/cleanob/src/openblock/ebpub/ebpub/media/scripts/
Alias /images/ /home/twilliams/cleanob/src/openblock/ebpub/ebpub/media/images/
Alias /cache-forever/ /home/twilliams/cleanob/src/openblock/ebpub/ebpub/media/cache-forever/
Alias /olwidget/ /home/twilliams/cleanob/lib/python2.7/site-packages/olwidget/static/olwidget/
Alias /resources/ /home/twilliams/cleanob/src/obcolumbia/obcolumbia/resources/
Alias /map_icons/ /home/twilliams/cleanob/src/obcolumbia/obcolumbia/resources/map_icons/

