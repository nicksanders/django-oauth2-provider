# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import urlparse
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, QueryDict
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView

from oauth2.models import Client, ClientStatus
from . import constants, scope
from provider.compat.http import JsonResponse
from provider.oauth2.models import AccessToken as AccessTokenModel


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class OAuthError(Exception):
    """
    Exception to throw inside any views defined in :attr:`provider.views`.

    Any :attr:`OAuthError` thrown will be signalled to the API consumer.

    :attr:`OAuthError` expects a dictionary as its first argument outlining the
    type of error that occured.

    :example:

    ::

        raise OAuthError({'error': 'invalid_request'})

    The different types of errors are outlined in :rfc:`4.2.2.1` and
    :rfc:`5.2`.

    """


class OAuthView(TemplateView):
    """
    Base class for any view dealing with the OAuth flow. This class overrides
    the dispatch method of :attr:`TemplateView` to add no-caching headers to
    every response as outlined in :rfc:`5.1`.
    """

    def dispatch(self, request, *args, **kwargs):
        response = super(OAuthView, self).dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Pragma'] = 'no-cache'
        return response


class Mixin(object):
    """
    Mixin providing common methods required in the OAuth view defined in
    :attr:`provider.views`.
    """
    def get_data(self, request, key='params'):
        """
        Return stored data from the session store.

        :param key: `str` The key under which the data was stored.
        """
        return request.session.get('{}:{}'.format(constants.SESSION_KEY, key))

    def cache_data(self, request, data, key='params'):
        """
        Cache data in the session store.

        :param request: :attr:`django.http.HttpRequest`
        :param data: Arbitrary data to store.
        :param key: `str` The key under which to store the data.
        """
        request.session['{}:{}'.format(constants.SESSION_KEY, key)] = data

    def clear_data(self, request):
        """
        Clear all OAuth related data from the session store.
        """
        for key in request.session.keys():
            if key.startswith(constants.SESSION_KEY):
                del request.session[key]

    def authenticate(self, request):
        """
        Authenticate a client against all the backends configured in
        :attr:`authentication`.
        """
        for backend in self.authentication:
            client = backend().authenticate(request)
            if client is not None:
                return client
        return None


class Capture(OAuthView, Mixin):
    """
    As stated in section :rfc:`3.1.2.5` this view captures all the request
    parameters and redirects to another URL to avoid any leakage of request
    parameters to potentially harmful JavaScripts.

    This application assumes that whatever web-server is used as front-end will
    handle SSL transport.

    If you want strict enforcement of secure communication at application
    level, set :attr:`settings.OAUTH_ENFORCE_SECURE` to ``True``.

    The actual implementation is required to override :meth:`get_redirect_url`.
    """
    template_name = 'provider/authorize.html'

    def get_redirect_url(self, request):
        """
        Return a redirect to a URL where the resource owner (see :rfc:`1`)
        authorizes the client (also :rfc:`1`).

        :return: :class:`django.http.HttpResponse`

        """
        raise NotImplementedError

    def handle(self, request, data):
        self.cache_data(request, data)

        if constants.ENFORCE_SECURE and not request.is_secure():
            return self.render_to_response({'error': 'access_denied',
                'error_description': _("A secure connection is required."),
                'next': None},
                status=400)

        response = HttpResponse("", status=302)
        response['Location'] = self.get_redirect_url(request)
        return response

    def get(self, request):
        return self.handle(request, request.GET)

    def post(self, request):
        return self.handle(request, request.POST)


class Authorize(OAuthView, Mixin):
    """
    View to handle the client authorization as outlined in :rfc:`4`.
    Implementation must override a set of methods:

    * :attr:`get_redirect_url`
    * :attr:`get_request_form`
    * :attr:`get_authorization_form`
    * :attr:`get_client`
    * :attr:`save_authorization`

    :attr:`Authorize` renders the ``provider/authorize.html`` template to
    display the authorization form.

    On successful authorization, it redirects the user back to the defined
    client callback as defined in :rfc:`4.1.2`.

    On authorization fail :attr:`Authorize` displays an error message to the
    user with a modified redirect URL to the callback including the error
    and possibly description of the error as defined in :rfc:`4.1.2.1`.
    """
    template_name = 'provider/authorize.html'

    def get_redirect_url(self, request):
        """
        :return: ``str`` - The client URL to display in the template after
            authorization succeeded or failed.
        """
        raise NotImplementedError

    def get_request_form(self, client, data):
        """
        Return a form that is capable of validating the request data captured
        by the :class:`Capture` view.
        The form must accept a keyword argument ``client``.
        """
        raise NotImplementedError

    def get_authorization_form(self, request, client, data, client_data):
        """
        Return a form that is capable of authorizing the client to the resource
        owner.

        :return: :attr:`django.forms.Form`
        """
        raise NotImplementedError

    def get_client(self, client_id):
        """
        Return a client object from a given client identifier. Return ``None``
        if no client is found. An error will be displayed to the resource owner
        and presented to the client upon the final redirect.
        """
        raise NotImplementedError

    def save_authorization(self, request, client, form, client_data):
        """
        Save the authorization that the user granted to the client, involving
        the creation of a time limited authorization code as outlined in
        :rfc:`4.1.2`.

        Should return ``None`` in case authorization is not granted.
        Should return a string representing the authorization code grant.

        :return: ``None``, ``str``
        """
        raise NotImplementedError

    def _validate_client(self, request, data):
        """
        :return: ``tuple`` - ``(client or False, data or error)``
        """
        client = self.get_client(data.get('client_id'))

        if client is None:
            raise OAuthError({
                'error': 'unauthorized_client',
                'error_description': _("An unauthorized client tried to access"
                    " your resources.")
            })
        elif client.status == ClientStatus.DISABLED:
            raise OAuthError({
                'error': 'disabled_client',
                'error_description': _("A disabled client tried to access"
                    " your resources.")
            })

        form = self.get_request_form(client, data)

        if not form.is_valid():
            raise OAuthError(form.errors)

        return client, form.cleaned_data

    def error_response(self, request, error, **kwargs):
        """
        Return an error to be displayed to the resource owner if anything goes
        awry. Errors can include invalid clients, authorization denials and
        other edge cases such as a wrong ``redirect_uri`` in the authorization
        request.

        :param request: :attr:`django.http.HttpRequest`
        :param error: ``dict``
            The different types of errors are outlined in :rfc:`4.2.2.1`
        """
        ctx = {}
        ctx.update(error)

        # If we got a malicious redirect_uri or client_id, remove all the
        # cached data and tell the resource owner. We will *not* redirect back
        # to the URL.

        if error['error'] in ['redirect_uri', 'unauthorized_client']:
            ctx.update(next='/')
            return self.render_to_response(ctx, **kwargs)

        ctx.update(next=self.get_redirect_url(request))

        return self.render_to_response(ctx, **kwargs)

    def handle(self, request, post_data=None):
        data = self.get_data(request)

        if data is None:
            return self.error_response(request, {
                'error': 'expired_authorization',
                'error_description': _('Authorization session has expired.')})

        try:
            client, data = self._validate_client(request, data)
        except OAuthError as e:
            form_errors = e.args[0]
            if 'error' not in form_errors:
                new_error = None
                for err, desc in form_errors.iteritems():
                    if err in ['redirect_uri', 'unauthorized_client']:
                        new_error = OAuthError({
                            'error': err,
                            'error_description': _(desc[0])
                        })
                        break
                if new_error is None:
                    logger.exception(e)
                    new_error = OAuthError({
                        'error': 'unknown_error',
                        'error_description': _(form_errors.items()[0][1])
                    })
                e = new_error
            return self.error_response(request, e.args[0], status=400)

        authorization_form = self.get_authorization_form(request, client,
            post_data, data)

        already_authorized = False
        if post_data is None and request.user.is_authenticated():
            already_authorized = \
                AccessTokenModel.objects.filter(client=client,
                                                   user=request.user,
                                                   scope=data.get('scope'),
                                                   expires__gte=now()).count() > 0
            if already_authorized:
                post_data = {
                    'client_id': str(client.pk),
                    'scope': ' '.join(scope.to_names(data.get('scope'))),
                    'redirect_uri': data.get('redirect_uri'),
                    'state': data.get('state'),
                    'authorize': 'Non-empty'
                }
                authorization_form = self.get_authorization_form(request, client, post_data, data)
                authorization_form.is_valid() # evaluate

        if not already_authorized and not authorization_form.is_valid():
            return self.render_to_response({
                'client': client,
                'form': authorization_form,
                'oauth_data': data, })

        code = self.save_authorization(request, client,
            authorization_form, data)

        # be sure to serialize any objects that aren't natively json
        # serializable because these values are stored as session data
        self.cache_data(request, data)
        self.cache_data(request, code, "code")
        self.cache_data(request, client.serialize(), "client")

        response = HttpResponse("", status=302)
        response['Location'] = self.get_redirect_url(request)
        return response

    def get(self, request):
        return self.handle(request, None)

    def post(self, request):
        return self.handle(request, request.POST)


class Redirect(OAuthView, Mixin):
    """
    Redirect the user back to the client with the right query parameters set.
    This can be either parameters indicating success or parameters indicating
    an error.
    """

    def error_response(self, error, content_type='application/json', status=400,
            **kwargs):
        """
        Return an error response to the client with default status code of
        *400* stating the error as outlined in :rfc:`5.2`.
        """
        return JsonResponse(error, status=status, **kwargs)

    def get(self, request):
        data = self.get_data(request)
        code = self.get_data(request, "code")
        error = self.get_data(request, "error")
        client = self.get_data(request, "client")

        # client must be properly deserialized to become a valid instance
        # but only if it has been serialized in the first place
        try:
            client = Client.deserialize(client)
        except:
            if not isinstance(client, Client):
                raise

        # this is an edge case that is caused by making a request with no data
        # it should only happen if this view is called manually, out of the
        # normal capture-authorize-redirect flow.
        if data is None or client is None:
            return self.error_response({
                'error': 'invalid_data',
                'error_description': _('Data has not been captured')})

        redirect_uri = data.get('redirect_uri', None) or client.redirect_uri.split(" ")[0]

        parsed = urlparse.urlparse(redirect_uri)

        # maybe it should looks like so??
        #query = QueryDict(parsed[4], mutable=True)
        query = QueryDict('', mutable=True)

        if 'state' in data:
            query['state'] = data['state']

        if error is not None:
            query.update(error)
        elif code is None:
            query['error'] = 'access_denied'
        else:
            query['code'] = code

        parsed = parsed[:4] + (query.urlencode(), '')

        redirect_uri = urlparse.ParseResult(*parsed).geturl()

        self.clear_data(request)

        response = HttpResponse("", status=302)
        response['Location'] = redirect_uri
        return response


class AccessToken(OAuthView, Mixin):
    """
    :attr:`AccessToken` handles creation and refreshing of access tokens.

    Implementations must implement a number of methods:

    * :attr:`get_authorization_code_grant`
    * :attr:`get_refresh_token_grant`
    * :attr:`get_password_grant`
    * :attr:`get_access_token`
    * :attr:`create_access_token`
    * :attr:`create_refresh_token`
    * :attr:`invalidate_grant`
    * :attr:`invalidate_access_token`
    * :attr:`invalidate_refresh_token`

    The default implementation supports the grant types defined in
    :attr:`grant_types`.

    According to :rfc:`4.4.2` this endpoint too must support secure
    communication. For strict enforcement of secure communication at
    application level set :attr:`settings.OAUTH_ENFORCE_SECURE` to ``True``.

    According to :rfc:`3.2` we can only accept POST requests.

    Returns with a status code of *400* in case of errors. *200* in case of
    success.
    """

    authentication = ()
    """
    Authentication backends used to authenticate a particular client.
    """

    grant_types = ['authorization_code', 'refresh_token', 'password',
                   'email_and_password', 'client_credentials']
    """
    The default grant types supported by this view.
    """

    def get_authorization_code_grant(self, request, data, client):
        """
        Return the grant associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, grant or error_dict)``
        """
        raise NotImplementedError

    def get_refresh_token_grant(self, request, data, client):
        """
        Return the refresh token associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, token or error_dict)``
        """
        raise NotImplementedError

    def get_password_grant(self, request, data, client):
        """
        Return a user associated with this request or an error dict.

        :return: ``tuple`` - ``(True or False, user or error_dict)``
        """
        raise NotImplementedError

    def get_client_credentials_grant(self, request, data, client):
        """
        Return the optional parameters (scope) associated with this request.
        :return: ``tuple`` - ``(True or False, options)``
        """
        raise NotImplementedError

    def get_access_token(self, request, user, scope, client):
        """
        Override to handle fetching of an existing access token.

        :return: ``object`` - Access token
        """
        raise NotImplementedError

    def create_access_token(self, request, user, scope, client):
        """
        Override to handle access token creation.

        :return: ``object`` - Access token
        """
        raise NotImplementedError

    def create_refresh_token(self, request, user, scope, access_token, client):
        """
        Override to handle refresh token creation.

        :return: ``object`` - Refresh token
        """
        raise NotImplementedError

    def update_refresh_token(self, refresh_token, access_token):
        """
        Override to handle refresh token updating. Bind the access token to
        the refresh token.

        :return None:
        """
        raise NotImplementedError

    def invalidate_grant(self, grant):
        """
        Override to handle grant invalidation. A grant is invalidated right
        after creating an access token from it.

        :return None:
        """
        raise NotImplementedError

    def invalidate_refresh_token(self, refresh_token):
        """
        Override to handle refresh token invalidation. When requesting a new
        access token from a refresh token, the old one is *always* invalidated.

        :return None:
        """
        raise NotImplementedError

    def invalidate_refresh_tokens_over_limit(self, user, scope, client, limit):
        """
        Override to handle refresh tokens invalidation to comply the limits.
        When limit number of refresh token is enabled, invalidate the oldest
        refresh tokens to comply with the limits.

        :return None:
        """
        raise NotImplementedError

    def invalidate_access_token(self, access_token):
        """
        Override to handle access token invalidation. When a new access token
        is created from a refresh token, the old one is *always* invalidated.

        :return None:
        """
        raise NotImplementedError

    def error_response(self, error, content_type='application/json', status=400,
            **kwargs):
        """
        Return an error response to the client with default status code of
        *400* stating the error as outlined in :rfc:`5.2`.
        """
        return JsonResponse(error, status=status, **kwargs)

    def access_token_response(self, access_token):
        """
        Returns a successful response after creating the access token
        as defined in :rfc:`5.1`.
        """

        response_data = {
            'access_token': access_token.token,
            'token_type': constants.TOKEN_TYPE,
            'expires_in': access_token.get_expire_delta(),
            'scope': ' '.join(scope.names(access_token.scope)),
        }

        # Not all access_tokens are given a refresh_token
        # (for example, public clients doing password auth)
        try:
            rt = access_token.refresh_token
            response_data['refresh_token'] = rt.token
        except ObjectDoesNotExist:
            pass

        return JsonResponse(response_data)

    def authorization_code(self, request, data, client):
        """
        Handle ``grant_type=authorization_code`` requests as defined in
        :rfc:`4.1.3`.
        """
        grant = self.get_authorization_code_grant(request, request.POST,
                client)
        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, grant.user, grant.scope, client)
        else:
            at = self.create_access_token(request, grant.user, grant.scope, client)
            rt = self.create_refresh_token(request, grant.user, grant.scope, at, client)
            if constants.LIMIT_NUM_REFRESH_TOKEN > 0:
                self.invalidate_refresh_tokens_over_limit(
                    grant.user, grant.scope, client, constants.LIMIT_NUM_REFRESH_TOKEN)

        self.invalidate_grant(grant)

        return self.access_token_response(at)

    def refresh_token(self, request, data, client):
        """
        Handle ``grant_type=refresh_token`` requests as defined in :rfc:`6`.
        """
        rt = self.get_refresh_token_grant(request, data, client)

        # this must be called first in case we need to purge expired tokens
        if not constants.KEEP_REFRESH_TOKEN:
            self.invalidate_refresh_token(rt)
        self.invalidate_access_token(rt.access_token)

        at = self.create_access_token(request, rt.user, rt.access_token.scope,
                client)
        if not constants.KEEP_REFRESH_TOKEN:
            rt = self.create_refresh_token(request, at.user, at.scope, at, client)
        else:
            self.update_refresh_token(rt, at)

        return self.access_token_response(at)

    def password(self, request, data, client):
        """
        Handle ``grant_type=password`` requests as defined in :rfc:`4.3`.
        """

        try:
            data = self.get_password_grant(request, data, client)
        except OAuthError, e:
            status = 400
            if e.args[0]['error'] == 'invalid_credentials':
                status = 401
            elif e.args[0]['error'] == 'invalid_scope':
                status = 403
            return self.error_response(e.args[0], status=status)
        user = data.get('user')
        scope = data.get('scope')

        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, user, scope, client)
        else:
            at = self.create_access_token(request, user, scope, client)
            # Public clients don't get refresh tokens
            if client.client_type == constants.CONFIDENTIAL:
                rt = self.create_refresh_token(request, user, scope, at, client)
                if constants.LIMIT_NUM_REFRESH_TOKEN > 0:
                    self.invalidate_refresh_tokens_over_limit(
                        user, scope, client, constants.LIMIT_NUM_REFRESH_TOKEN)

        return self.access_token_response(at)

    def email_and_password(self, request, data, client):
        """
        Handle ``grant_type=email_and_password`` requests.
        """

        data = self.get_email_and_password_grant(request, data, client)
        user = data.get('user')
        scope = data.get('scope')

        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, user, scope, client)
        else:
            at = self.create_access_token(request, user, scope, client)
            # Public clients don't get refresh tokens
            if client.client_type == constants.CONFIDENTIAL:
                rt = self.create_refresh_token(request, user, scope, at, client)

        return self.access_token_response(at)

    def client_credentials(self, request, data, client):
        """
        Handle ``grant_type=client_credentials`` requests as defined in
        :rfc:`4.4`.
        """
        data = self.get_client_credentials_grant(request, data, client)
        scope = data.get('scope')

        # Client credentials should operate on public data and the
        # client only -- exposing the user has the potential to compromise
        # other assets associated with the user but not necessarily the client
        if constants.SINGLE_ACCESS_TOKEN:
            at = self.get_access_token(request, None, scope, client, refreshable=False)
        else:
            at = self.create_access_token(request, None, scope, client)

        return self.access_token_response(at)

    def get_handler(self, grant_type):
        """
        Return a function or method that is capable handling the ``grant_type``
        requested by the client or return ``None`` to indicate that this type
        of grant type is not supported, resulting in an error response.
        """
        if grant_type == 'authorization_code':
            return self.authorization_code
        elif grant_type == 'refresh_token':
            return self.refresh_token
        elif grant_type == 'password':
            return self.password
        elif grant_type == 'email_and_password':
            return self.email_and_password
        elif grant_type == 'client_credentials':
            return self.client_credentials
        return None

    def get(self, request):
        """
        As per :rfc:`3.2` the token endpoint *only* supports POST requests.
        Returns an error response.
        """
        return self.error_response({
            'error': 'invalid_request',
            'error_description': _("Only POST requests allowed.")})

    def post_response(self, request):
        """
        As per :rfc:`3.2` the token endpoint *only* supports POST requests.
        """
        if constants.ENFORCE_SECURE and not request.is_secure():
            return self.error_response({
                'error': 'invalid_request',
                'error_description': _("A secure connection is required.")})

        if not 'grant_type' in request.POST:
            return self.error_response({
                'error': 'invalid_request',
                'error_description': _("No 'grant_type' included in the "
                    "request.")})

        grant_type = request.POST['grant_type']

        if grant_type not in self.grant_types:
            return self.error_response({'error': 'unsupported_grant_type'})

        client = self.authenticate(request)

        if client is None:
            return self.error_response({'error': 'invalid_client'}, status=404)

        handler = self.get_handler(grant_type)

        try:
            return handler(request, request.POST, client)
        except OAuthError, e:
            return self.error_response(e.args[0])

    def post(self, request):
        response = self.post_response(request)

        grant_type = request.POST.get('grant_type', None)

        if grant_type == 'password':
            return self.add_allow_cors_header_to_response(request, response)
        else:
            return response

    def options(self, request, *args, **kwargs):
        return self.add_allow_cors_header_to_response(request,
                                                      super(AccessToken, self).options(request, *args, **kwargs))

    def add_allow_cors_header_to_response(self, request, response):
        if request.META.has_key('HTTP_ORIGIN'):
            response['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
            response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return response
