# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponse
from django.utils.functional import SimpleLazyObject
from django.utils.timezone import now

from provider.oauth2.models import AccessToken

__author__ = 'amaru'

class HttpResponseUnauthorized(HttpResponse):
    status_code = 401


def _get_user(request):
    oauth_token = None
    try:
        auth_header = request.META['HTTP_AUTHORIZATION']
        if auth_header.startswith('token'):
            try:
                oauth_token = auth_header.split(' ')[1]
            except IndexError:
                return AnonymousUser()
    except KeyError:
        pass

    if not oauth_token:
        try:
            oauth_token = request.GET['access_token']
        except KeyError:
            pass

    if not oauth_token:
        try:
            oauth_token = request.POST['access_token']
        except KeyError:
            pass

    if not oauth_token:
        try:
            oauth_token = request.COOKIES['at']
        except KeyError:
            pass

    if not oauth_token:
        return AnonymousUser()

    try:
        token = AccessToken.objects.get(token=oauth_token, expires__gt=now(), user__is_active=True)
    except AccessToken.DoesNotExist:
        return AnonymousUser()

    try:
        return get_user_model().objects.get(pk=token.user_id)
    except get_user_model().DoesNotExist:
        return AnonymousUser()


def get_user(request):
    if not hasattr(request, '_cached_user'):
        request._cached_user = _get_user(request)
    return request._cached_user


class AuthenticationMiddleware(object):
    """
    Checks the incoming requests for a valid authentication mechanism.
    Authentication mechanisms allowed are (in order of preference):
    1. Header: "Authorization: token <OAUTH-TOKEN>"
    2. Http params: "access_token=<OAUTH-TOKEN>"
    3. (Unsupported) Header: "Authorization: client_id <ID> client_secret <SECRET>" // public requests where user isn't
    required
    4. (Unsupported) Http params: "client_id=<ID>&client_secret=<SECRET>" // public requests where user isn't required
    5. Cookie: at=<OAUTH-TOKEN>

    If a path requires an authenticated user, and none is presented, the method would return 401 access denied.
    """

    def process_request(self, request):
        request.user = SimpleLazyObject(lambda: get_user(request))
        return None
