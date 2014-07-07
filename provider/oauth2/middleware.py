from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponse
from django.utils.functional import SimpleLazyObject
from django.utils.timezone import now
from provider.oauth2.models import AccessToken

__author__ = 'amaru'

class HttpResponseUnauthorized(HttpResponse):
    status_code = 401


class AuthenticationMiddleware(object):
    '''
    Checks the incoming requests for a valid authentication mechanism.
    Authentication mechanisms allowed are (in order of preference):
    1. Header: "Authorization: token <OAUTH-TOKEN>"
    2. Http params: "__oauth_token=<OAUTH-TOKEN>"
    3. (Unsupported) Header: "Authorization: client_id <ID> client_secret <SECRET>" // public requests where user isn't
    required
    4. (Unsupported) Http params: "client_id=<ID>&client_secret=<SECRET>" // public requests where user isn't required

    If a path requires an authenticated user, and none is presented, the method would return 401 access denied.
    '''
    def process_request(self, request):
        oauth_token = None
        try:
            auth_header = request.META['HTTP_AUTHORIZATION']
            if auth_header.startswith('token'):
                try:
                    oauth_token = auth_header.split(' ')[1]
                except IndexError:
                    return HttpResponseUnauthorized()
        except KeyError:
            pass

        if not oauth_token:
            try:
                oauth_token = request.GET['__oauth_token']
            except KeyError:
                pass

        if not oauth_token:
            try:
                oauth_token = request.POST['__oauth_token']
            except KeyError:
                pass

        if not oauth_token:
            return HttpResponseUnauthorized()

        try:
            token = AccessToken.objects.get(token=oauth_token, expires__gt=now(), user__is_active=True)
        except AccessToken.DoesNotExist:
            return HttpResponseUnauthorized()

        request.user = SimpleLazyObject(lambda: get_user_model().objects.get(pk=token.user_id))
        return None