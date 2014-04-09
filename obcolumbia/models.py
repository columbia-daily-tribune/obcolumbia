from django.contrib.gis.db import models
from ebpub.db.models import Schema, post_update
from django.db.models.signals import post_save, post_delete

class SchemaRestriction(models.Model):
    """
    Create one of these to mark some Schemas as 'premium' content.

    More than one of these could be created if you want to have
    multiple levels of access.
    """

    description = models.CharField(max_length=256,
                                   help_text='Just a label for use in the admin UI.',
                                   default='Active subscription required')
    schemas = models.ManyToManyField(
        Schema,
        null=True,
        help_text='Which schemas this restriction applies to.')

    subscriber_status = models.CharField(
        max_length=256, null=False,
        default='is_active',
        help_text='Required subscriber status users must have to see news of these types. Must be unique to a single Schema Restriction instance.  You probably only need one Schema Restriction',
        db_index=True)

    def __unicode__(self):
        return self.description


###############################################################################
# Signals

def clear_more_schema_id_cache(sender, **kwargs):
    from django.core.cache import cache
    from obcolumbia.utils import ACTIVE_KEY, ANON_KEY, INACTIVE_KEY
    cache.delete_many((ACTIVE_KEY, ANON_KEY, INACTIVE_KEY))

post_update.connect(clear_more_schema_id_cache, sender=Schema)
post_save.connect(clear_more_schema_id_cache, sender=Schema)
post_delete.connect(clear_more_schema_id_cache, sender=Schema)

