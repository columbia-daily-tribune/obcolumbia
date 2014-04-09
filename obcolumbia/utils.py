from ebpub.db import constants
from ebpub.db.models import Schema
from django.core.cache import cache
from django.db.models.query import QuerySet
import copy
import logging

logger = logging.getLogger('obcolumbia.utils')

_cache_key_root='allowed_schema_ids_obcolumbia'

ACTIVE_KEY = _cache_key_root + '-active'
INACTIVE_KEY = _cache_key_root + '-inactive'
ANON_KEY = INACTIVE_KEY  # This could change, but for now anonymous and inactive see the same stuff

def schema_manager_filter(user, manager):
    """
    Returns a Manager that can override the Schemas that are allowed,
    based on current user.
    """
    # We do this via monkeypatching the manager instance rather than
    # subclassing because I'm not sure what behavior this will need to
    # grow to support, and I don't want to proliferate a bunch of
    # Manager subclasses and have to figure out how to register them
    # on an already-existing model.  Maybe that's silly, but this
    # works fine.
    if getattr(manager, '_patched_qs', False):
        return manager

    manager = copy.copy(manager)

    can_see_premium = False
    cachekey = None

    if user.is_authenticated():
        if user.is_superuser:
            logger.debug("Superuser %s can see premium content" % user)
            return manager

        if is_subscriber(user):
            logger.debug("Active subscriber %s can see premium content" % user)
            can_see_premium = True
            cachekey = ACTIVE_KEY
        else:
            logger.debug("No premium content: %s is not active subscriber" % user)
            cachekey = INACTIVE_KEY
    else:
        logger.debug("Anonymous can't see premium content")
        cachekey = INACTIVE_KEY  # ANON_KEY

    if not can_see_premium:
        qs = QuerySet(manager.model, using=manager._db)

        def allowed_schema_ids():
            """
            PATCHED by obcolumbia!
            """
            result = cache.get(cachekey, None)
            if result is None:
                from obcolumbia.models import SchemaRestriction
                try:
                    restriction = SchemaRestriction.objects.get(subscriber_status='is_active')
                    # TODO: this should query only the intermediate
                    # table; does it hit the Schema table??
                    prohibited_ids = [s['id'] for s in restriction.schemas.all().values('id')]
                    result = qs.exclude(id__in=prohibited_ids)
                except SchemaRestriction.DoesNotExist:
                    result = qs.all()
                result = [r['id'] for r in result.values('id')]
                cache.set(cachekey, result, constants.ALLOWED_IDS_CACHE_TIME)
            return result


        def get_query_set():
            """
            PATCHED by obcolumbia!
            """
            return Schema.objects.filter(id__in=allowed_schema_ids())

        manager.get_query_set = get_query_set
        manager.allowed_schema_ids = allowed_schema_ids
        manager._patched_qs = True
    return manager

def neighbornews_use_captcha(request):
    """
    Whether to use captcha depends on user's subscription status.
    """
    user = request.user
    if user.is_authenticated():
        if user.is_superuser:
            logger.debug("Superuser %s doesn't need captcha" % user)
            return False

        if is_subscriber(user):
            logger.debug("Active subscriber %s doesn't need captcha" % user)
            return False
        else:
            logger.debug("Captcha needed: %s is not active subscriber" % user)
            return True

    logger.debug("Anonymous needs captcha")
    return True


def is_subscriber(user):
    profile = user.get_profile()
    subscriber_info = profile.properties.get('subscriber_info', {})
    return subscriber_info.get('is_active', False)
