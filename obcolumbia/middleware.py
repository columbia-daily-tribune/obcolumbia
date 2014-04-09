from django.conf import settings
from ebpub.accounts.models import AnonymousUser
from obcolumbia.views import get_user_info_from_request
from obcolumbia.views import maybe_update_profile
import logging


logger = logging.getLogger('obcolumbia.middleware')

def do_logout(request):
    request.session.flush()
    request.user = AnonymousUser()

class OauthRefreshMiddleware(object):
    """
    Every so often, if user is logged in, check that
    our oauth tokens are still valid; if not, log out.

    Must come after ebpub.accounts.middleware.UserMiddleware.
    """
    def process_request(self, request):
        if not 'oauth_login' in getattr(settings, 'LOGIN_VIEW'):
            return None
        if request.user.is_anonymous():
            return None
        if not request.session.get('logged_in_via_obcolumbia_oauth'):
            # Probably logged in using one of the standard backends / forms.
            # So, don't mess with anything.
            return None
        # Now check the oauth tokens, if they're old.
        info = get_user_info_from_request(request)
        if info.get('error'):
            logger.info(info['error'])
            do_logout(request)
        else:
            profile = request.user.get_profile()
            maybe_update_profile(profile, info)
        return None
