# -*- coding: latin-1 -*

"""
Custom OpenBlock views for Columbia site.
"""

from ebpub.metros.allmetros import get_metro
from ebpub.utils.view_utils import eb_render
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
import httplib2
import json
import logging
import oauth2 as oauth
import pprint
import time
import urllib
import urlparse

logger = logging.getLogger('obcolumbia.views')


def login(request):
    """
    View that uses different login functions depending on settings.

    If for logging in via OAuth (protocol version 1).

    If an email & password is in request.POST, this will always use
    the old password-based login.

    If settings.LOGIN_FUNCTION is set, it should be a string giving
    the path to a function to import and use.
    Possible options are ' USE_OAUTH_LOGIN is True,
    it uses :py:func:`oauth_login`

    If settings.USE_BLOX_LOGIN is True, it uses :py:func:`blox_login`.

    If user is already logged in, we redirect back where you were,
    or to your dashboard.
    """
    # First check if we're already logged in.
    if not request.user.is_anonymous():
        logger.debug('login view: Already logged in')
        # If the user is already logged in, redirect to the dashboard.
        next_url = request.session.get('next') or reverse('accounts-dashboard')
        return HttpResponseRedirect(next_url)

    # Then try vanilla password-based login.
    from ebpub.accounts.views import login as vanilla_login
    if 'email' in request.POST and 'password' in request.POST:
        logger.debug('login view: using email and password')
        return vanilla_login(request)

    # Otherwise check if there's a configured login view function.
    login_view_name = getattr(settings, 'LOGIN_VIEW', None)
    if login_view_name is not None:
        logger.debug('login view: using function named %r' % login_view_name)
        module, func = login_view_name.split(':')
        import importlib
        module = importlib.import_module(module)
        func = getattr(module, func)
        logger.debug('login view: got function %s from %s' % (func, module))
        return func(request)
    else:
        logger.debug('login view: fall back to vanilla login')
        return vanilla_login(request)


def blox_login(request):
    """
    Log in using TownNews BLOX CMS Federated Login API.

    See http://docs.townnews.com/kbpublisher/index.php?View=entry&EntryID=6695
    and search for "federated login API". (No direct link, weird iframes site)

    Terminology:
    * Provider: The TNCMS site.
    * Consumer: The OpenBlock site (the external site that a TNCMS
      user wants to log in to.)
    * User: The account holder and the browser she is controlling.
    """
    if True:
        blox_url = getattr(settings, 'BLOX_PROVIDER_URL', u'').rstrip('/').strip()
        if not blox_url:
            raise RuntimeError("You can't use blox_login() without settings.BLOX_PROVIDER_URL")
        if not blox_url.startswith('https://'):
            logger.warn('Getting user data from settings.BLOX_PROVIDER_URL (%s) will be insecure! Use https:// if possible!' % blox_url)

        params = {'return': request.build_absolute_uri()}
        provider_auth_url = '%s/tncms/auth/federated/?%s' % (blox_url, urllib.urlencode(params))

        blox_key = getattr(settings, 'BLOX_API_KEY', u'').strip()
        blox_secret = getattr(settings, 'BLOX_API_SECRET', u'').strip()
        if not (blox_key and blox_secret):
            raise RuntimeError("You can't use blox_login() without both settings.BLOX_API_KEY and settings.BLOX_API_SECRET")

        if not 'code' in request.GET:
            # 1. The consumer site redirects the user to the provider site's
            # federated authentication endpoint.
            # Must include the 'return' parameter to redirect back to.
            return HttpResponseRedirect(provider_auth_url)

        # 2. The user submits authentication details to the provider site as needed.
        # 3. The provider site redirects the user back to the consumer
        # site’s endpoint along with an authentication code.
        code = request.GET['code']

        # 4. The consumer site performs a webservice call to the provider
        # site to exchange the authentication code for the user’s account
        # details.
        user_info_url = '%s/tncms/webservice/v1/user/get/?code=%s' % (blox_url, code)
        http = httplib2.Http()
        http.add_credentials(blox_key, blox_secret)
        resp, content = http.request(user_info_url)
        status_code = int(resp['status'])

        try:
            result = json.loads(content)
        except ValueError:
            result = {'code': str(status_code), 'status': 'error', 'message': 'no valid JSON data received'}

        if status_code >= 400:
            return HttpResponse("Error code: %(code)s, message: %(message)s" % result, status=401)

    if False:  # Testing
        result = {'screen_name': 'slinkytest',
                  'email': 'pw+slinkytest@openplans.org',
                  'status': 'active',
                  }
    # We don't have separate 'user' and 'subscriber' info, but we use both later.
    user_info = {'user': {'email': result['email']},
                 'subscriber': result}
    # See https://docs.google.com/document/pub?id=1XqxUHNsOjBVFs9lOgSt_sz5djA0mYD_mKsincmQh120#h.oa2cf6y4rw5a
    user_info['access_token'] = 'unused'  # this isn't OAuth, but we check for its presence later.
    set_user_info_on_session(request.session, user_info)
    # 5. The user is now considered logged in to the consumer site.
    return handle_federated_login(request, user_info)



def oauth_login(request):
    """
    Terminology: Consumer = 'client' in more recent oauth terminology
    - this is the site that wants to access the oauth-protected
    resources.

    Provider = 'server' (oauth authentication server).  That's
    Ellington.

    User = the person/computer interacting with the consumer/client.
    """

    consumer = oauth.Consumer(settings.OAUTH_CONSUMER_KEY,
                              settings.OAUTH_CONSUMER_SECRET)
    # We use our own URI as the callback for the provider to redirect to.
    body_params = {'oauth_callback': request.build_absolute_uri()}
    if getattr(settings, 'OAUTH_SCOPE', ''):
        body_params['scope'] = settings.OAUTH_SCOPE
    body = urllib.urlencode(body_params)

    if not ('oauth_token' in request.GET):
        # Step 1: Get a request token. This is a temporary token
        # that is used for having the user authorize an access
        # token and to sign the request to obtain said access
        # token.
        logger.info("No oauth_token, getting a request token")
        client = oauth.Client(consumer)
        # # For debugging this can be useful to see what's going on
        #client.set_signature_method(oauth.SignatureMethod_PLAINTEXT())
        token_url = settings.OAUTH_REQUEST_TOKEN_URL
        try:
            resp, content = client.request(token_url, "POST", body=body)
        except AttributeError:
            # Httplib2 bug.
            return HttpResponse("OAuth: couldn't connect to server.",
                                status=401)
        if resp['status'] != '200':
            logger.info("Response %s from %s:\n%s" % (resp['status'], token_url,
                                                      content))
            return HttpResponse(
                "OAuth: couldn't get request token:  Invalid response %s." % resp['status'],
                status=401)

        request.session['request_token'] = content

        request_token = dict(urlparse.parse_qsl(content))
        # Step 2: Redirect to the provider, with the request token.
        logger.info("Redirecting to provider with request token.")
        url = '%s?oauth_token=%s' % (
            settings.OAUTH_AUTHORIZE_URL, request_token['oauth_token'])
        return HttpResponseRedirect(url)

    elif 'oauth_verifier' in request.GET and 'oauth_token' in request.GET:
        # Step 3: Once the client ("consumer") has redirected the
        # user back to the oauth_callback URL, you can request the
        # access token the user has approved. You use the request
        # token to sign this request. After this is done you throw
        # away the request token and use the access token
        # returned. You should store this access token somewhere
        # safe, like a database, for future use.
        logger.info("Got oauth_verifier, retrieving access token.")
        try:
            request_token = dict(urlparse.parse_qsl(request.session.pop('request_token')))
        except KeyError:
            return HttpResponse("Login via OAuth failed: missing request_token",
                                status=401)

        token = oauth.Token(request_token['oauth_token'],
                            request_token['oauth_token_secret'])
        token.set_verifier(request.GET['oauth_verifier'])
        client = oauth.Client(consumer, token)

        # If that's the correct verifier, we should successfully
        # retrieve the access token now.
        access_token_url = settings.OAUTH_ACCESS_TOKEN_URL
        resp, content = client.request(access_token_url, "POST", body)
        if resp['status'] != '200':
            logger.info("Response %s from %s:\n%s" % (resp['status'], access_token_url,
                                                      content))
            return HttpResponse(
                "Getting OAuth access token failed with status %s" % resp['status'],
                status=401)

        access_token = dict(urlparse.parse_qsl(content))
        # 4. Now we can access the protected resource on the provider.
        logger.info("Got access token, using it to fetch user info")
        user_info = fetch_ellington_user_info(access_token)
        if user_info.get('error'):
            return HttpResponse(
                "Getting user info failed: %s" % user_info['error'], status=401)

        user_info['access_token'] = access_token
        set_user_info_on_session(request.session, user_info)
        return handle_federated_login(request, user_info)


def fetch_ellington_user_info(access_token, url=settings.OAUTH_USER_INFO_URL):
    """
    Given a valid OAuth Access token, get user info from the provider.
    """
    consumer = oauth.Consumer(settings.OAUTH_CONSUMER_KEY,
                                      settings.OAUTH_CONSUMER_SECRET)

    token = oauth.Token(access_token['oauth_token'],
                        access_token['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    try:
        resp, content = client.request(url, "GET")
    except AttributeError:
        # Underlying httplib2 bug: "'NoneType' object has no attribute 'makefile'"
        return {'error': '500', 'content': 'Could not connect to OAuth provider'}
    if resp['status'] != '200':
        return {'error': resp['status'], 'content': content}

    user_info = json.loads(content)
    return user_info


def handle_federated_login(request, user_info):
    """
    Log in the user named by user_info['user']['email'],
    creating the account if necessary; and save user_info['access_token']
    and user_info['subscriber']
    in the user's profile.
    """
    # For OAuth, we use RemoteUserBackend, which doesn't require a password,
    # and creates the user if needed.
    # ... or not; we don't call authenticate() because it
    # only creates the django.contrib.auth User model,
    # not our custom wrapper.
    from ebpub.accounts.models import User
    try:
        email = user_info['user']['email']
        assert email
    except (KeyError, AssertionError):
        logger.info("Email missing in user info? %s" % pprint.pformat(user_info))
        return HttpResponse(
            "Federated login failed - no email address in subscriber info",
            status=401)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # This takes care of setting an unusable password, too.
        logger.info("Federated login: creating user account for %r" % email)
        user = User.objects.create_user(email=email)
    if user is not None:
        # Make sure we have latest access token and subscription info saved.
        profile = user.get_profile()
        user_info = get_user_info_from_request(request)
        maybe_update_profile(profile, user_info)
        # Finally, log in.
        if user.is_active:
            # login() expects a dotted name at user.backend. We don't have an
            # actual backend per se, and it doesn't matter what we put here,
            # but we still need to sacrifice this particular chicken.
            user.backend = 'obcolumbia.custom_backend'
            from ebpub.accounts import utils
            utils.login(request, user)
            # Keep track of how we logged in, so we can distinguish
            # oauth login sessions from password login sessions.
            request.session['logged_in_via_obcolumbia_oauth'] = True
            url = request.session.get('next') or reverse('ebpub-homepage')
            logger.debug("Federated login success: redirecting %s to %s" % (email, url))
            return HttpResponseRedirect(url)
        else:
            raise NotImplementedError("Need to handle inactive users?")
    else:
        return HttpResponse("Login via OAuth failed - got None from authenticate()",
                            status=401)

def logout(request):
    # Overriding this to avoid being automagically logged back in
    # right away, or just seeing the logout form again.
    from ebpub.accounts.views import logout as ebpub_logout
    result = ebpub_logout(request)
    if isinstance(result, HttpResponseRedirect):
        import urlparse
        path = urlparse.urlparse(result['location']).path
        # Unfortunately there is no way to introspect a view to see if it has
        # been decorated with login_required, and no way to test whether it's
        # allowed, short of calling it and checking for a redirect to login,
        # which would be goofy.
        # So, we list a bunch of views not to redirect to, and hope we get most
        # or all of them.
        avoid_redirect_loop_views = (
            login, 'admin-logout',
            'accounts-logout',
            'accounts-dashboard',
            'new_message', 'edit_message', 'delete_message',
            'new_event', 'edit_event', 'delete_event',
            )
        for view in avoid_redirect_loop_views:
            try:
                if path == reverse(view):
                    result['location'] = reverse('ebpub-homepage')
                    break
            except Exception:
                # Not sure what gets raised if reverse() fails,
                # eg. if neighbornews is not installed.  don't worry about
                # it.
                pass

    return result


###########################################################################
# Utility functions

def set_user_info_on_session(session, user_info):
    """Stash a bag of info on the session, with a timestamp.
    """
    user_info['refreshed'] = time.time()
    session['oauth_user_info'] = json.dumps(user_info)

def get_user_info_from_request(request):
    """Given a request, get (and set, if missing or expired) the user's
    info that we get from the oauth provider.
    """
    info = {}
    access_token = None
    if 'oauth_user_info' in request.session:
        info = json.loads(request.session['oauth_user_info'])
        access_token = info['access_token']
        logger.debug("ACCESS TOKEN FROM SESSION: %s" % str(access_token))
    else:
        # Missing? Try the one from the profile.
        access_token = request.user.get_profile().properties.get('access_token', None)
        logger.debug("ACCESS TOKEN FROM PROFILE: %s" % str(access_token))
    if access_token is None:
        return {'error': 'no access token found in session or profile'}

    refreshed = info.get('refreshed', 0)
    if refreshed + settings.OAUTH_REFRESH_TIMEOUT < time.time():
        # Check the access key again.
        info = fetch_ellington_user_info(access_token)
        if info.get('error'):
            logger.info("Problem with oauth refresh: response %s, content: %s"
                        % (info['error'], info['content']))
            return {'error': 'response %(error)s: %(content)s' % info}
        else:
            # Access token confirmed.
            info['access_token'] = access_token
            logger.debug("ACCESS TOKEN FROM REMOTE: %s" % str(access_token))
            set_user_info_on_session(request.session, info)
            profile = request.user.get_profile()
            maybe_update_profile(profile, info)

    return json.loads(request.session['oauth_user_info'])

def maybe_update_profile(profile, user_info):
    """
    If the the user_info's access_token or subscriber_info differ from
    what's in the profile, save them.
    """
    access_token = user_info.get('access_token', u'')
    subscriber_info = user_info.get('subscriber', {})
    if profile.properties.get('oauth_access_token') != access_token or \
            profile.properties.get('subscriber_info') != subscriber_info:
        logger.debug("Updating subscriber info for %s profile" % user_info['user']['email'])
        profile.properties['oauth_access_token'] = access_token
        profile.properties['subscriber_info'] = subscriber_info
        profile.save()


def homepage(request):
    """Override the front page to add a list of citywide news, a list of
    citywide events, a list of premium types, ...
    """
    from ebpub.db.views import _homepage_context
    from ebpub.db.views import _news_context
    context = _homepage_context(request)
    max_items = getattr(settings, 'MAX_HOMEPAGE_ITEMS', 5)
    recent_ni_context = _news_context(request, {}, max_items, show_upcoming=False)
    event_ni_context = _news_context(request, {}, max_items, show_upcoming=True)

    context['recent_news'] = list(recent_ni_context['newsitem_list'])
    context['upcoming_events'] = list(event_ni_context['newsitem_list'])

    # Pagination stuff. We're showing two lists so we need two batches of pagination
    # params.
    # We only have one "page" parameter though; hopefully that's not too confusing.
    context.update({
        'recent_has_next': recent_ni_context['has_next'],
        'recent_has_previous': recent_ni_context['has_previous'],
        'recent_page_number': recent_ni_context['page_number'],
        'recent_previous_page_number': recent_ni_context['previous_page_number'],
        'recent_next_page_number': recent_ni_context['next_page_number'],
        'recent_page_start_index': recent_ni_context['page_start_index'],
        'recent_page_end_index': recent_ni_context['page_end_index'],
        'event_has_next': event_ni_context['has_next'],
        'event_has_previous': event_ni_context['has_previous'],
        'event_page_number': event_ni_context['page_number'],
        'event_previous_page_number': event_ni_context['previous_page_number'],
        'event_next_page_number': event_ni_context['next_page_number'],
        'event_page_start_index': event_ni_context['page_start_index'],
        'event_page_end_index': event_ni_context['page_end_index'],
        })


    context['bbox'] = get_metro()['extent']
    context['hidden_schema_list'] = recent_ni_context['hidden_schema_list']
    context['hidden_schema_list'].extend(event_ni_context['hidden_schema_list'])

    context['is_latest_page'] = True
    context['next_day'] = None
    context['place'] = None

    # We also need to know which schemas are 'premium' even if the
    # current user can see them. So we're overriding allowed_schema_ids
    # to only include non-premium ones.

    # There must be a clearer way to get just the IDs from a many-to-many
    # relationship.
    from ebpub.db.models import Schema
    from obcolumbia.models import SchemaRestriction
    try:
        restriction = SchemaRestriction.objects.get(subscriber_status='is_active')
        premium_ids = [v[0] for v in restriction.schemas.all().values_list('id')]

    except SchemaRestriction.DoesNotExist:
        premium_ids = []

    non_premium = Schema.public_objects.exclude(id__in=premium_ids)
    context['visible_allowed_schema_ids'] = context['allowed_schema_ids']
    context['allowed_schema_ids'] = [v[0] for v in non_premium.values_list('id')]

    return eb_render(request, 'homepage.html', context)
