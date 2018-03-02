#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#
import hashlib

from pyramid.view import forbidden_view_config
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.security import Everyone
from pyramid.security import Allow
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.interfaces import IAuthenticationPolicy
import pyramid_ipauth

from zope.interface import implements

HASHED_ADMIN_PASSWORD = '\x86\x19\xee\xfc\xd1la\x85\xb8\x11c\x1dg\xe6rs\xad\xd6\xb2\xbd\x87Sb\xe1\x9c\x85\x93\xder\xe1\xa9\xfe\x80\xea\xaf\xe5jhm\x16\x90\x1c\x12O\xd4FW\xc3a\xcdb.\x19C\x9a\xb7[\xda.5>\x9c\x89C'


class Root(object):
    def __init__(self, request):
        self.request = request

    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, 'locals', 'write'),
    ]


def _hash_password(password):
    t_sha = hashlib.sha512()
    t_sha.update(password)
    return t_sha.digest()


def check_username(credentials, request):
    if credentials.keys() == ['login', 'password']:
        if credentials['login'] == 'admin' and _hash_password(credentials['password']) == HASHED_ADMIN_PASSWORD:
            return ['locals']
    return HTTPUnauthorized()


@forbidden_view_config()
def forbidden_view(request):
    resp = HTTPUnauthorized()
    resp.www_authenticate = 'Basic realm="Secure Area"'
    return resp


def includeme(config):
    """
    This function provides a hook for pyramid to include the default settings
    for ip-based auth and fallback to http basic authentication.  Activate it like so:

        config.include("restrepo.security")

    """
    # Grab the pyramid-wide settings, to look for any auth config.
    settings = config.get_settings().copy()
    # Hook up a default AuthorizationPolicy.
    # ACLAuthorizationPolicy is usually what you want.
    # If the app configures one explicitly then this will get overridden.
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
    # Use the settings to construct an AuthenticationPolicy.
    ip_policy = pyramid_ipauth.IPAuthenticationPolicy.from_settings(settings)
    login_policy = BasicAuthenticationPolicy(check_username)
    auth_policy = Combine(ip_policy, login_policy)
    config.set_authentication_policy(auth_policy)


class Combine(object):
    implements(IAuthenticationPolicy)

    def __init__(self, *policies):
        self.policies = policies

    def make_finder(self):
        # todo: name = self????
        name = self

        def get_first_result(self, *args, **kwargs):
            for policy in self.policies:
                result = getattr(policy, name)(*args, **kwargs)
                if result:
                    return result
        return get_first_result

    def effective_principals(self, request):
        _all = sum((el.effective_principals(request) for el in self.policies), [])
        return list(set(_all))

    authenticated_userid = make_finder('authenticated_userid')
    unauthenticated_userid = make_finder('unauthenticated_userid')
    remember = make_finder('remember')
    forget = make_finder('forget')
    del make_finder


# Copied verbatim from http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/auth/basic.html

import binascii

from zope.interface import implements

from paste.httpheaders import AUTHORIZATION
from paste.httpheaders import WWW_AUTHENTICATE

from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone
from pyramid.security import Authenticated


def _get_basicauth_credentials(request):
    authorization = AUTHORIZATION(request.environ)
    try:
        authmeth, auth = authorization.split(' ', 1)
    except ValueError:  # not enough values to unpack
        return None
    if authmeth.lower() == 'basic':
        try:
            auth = auth.strip().decode('base64')
        except binascii.Error:  # can't decode
            return None
        try:
            login, password = auth.split(':', 1)
        except ValueError:  # not enough values to unpack
            return None
        return {'login': login, 'password': password}

    return None


class BasicAuthenticationPolicy(object):
    """ A :app:`Pyramid` :term:`authentication policy` which
    obtains data from basic authentication headers.

    Constructor Arguments

    ``check``

        A callback passed the credentials and the request,
        expected to return None if the userid doesn't exist or a sequence
        of group identifiers (possibly empty) if the user does exist.
        Required.

    ``realm``

        Default: ``Realm``.  The Basic Auth realm string.

    """
    implements(IAuthenticationPolicy)

    def __init__(self, check, realm='Realm'):
        self.check = check
        self.realm = realm

    def authenticated_userid(self, request):
        credentials = _get_basicauth_credentials(request)
        if credentials is None:
            return None
        userid = credentials['login']
        if self.check(credentials, request) is not None:  # is not None!
            return userid

    def effective_principals(self, request):
        effective_principals = [Everyone]
        credentials = _get_basicauth_credentials(request)
        if credentials is None:
            return effective_principals
        userid = credentials['login']
        groups = self.check(credentials, request)
        if groups is None:  # is None!
            return effective_principals
        effective_principals.append(Authenticated)
        effective_principals.append(userid)
        effective_principals.extend(groups)
        return effective_principals

    def unauthenticated_userid(self, request):
        creds = _get_basicauth_credentials(request)
        if creds is not None:
            return creds['login']
        return None

    def remember(self, request, principal, **kw):
        return []

    def forget(self, request):
        head = WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
        return head
