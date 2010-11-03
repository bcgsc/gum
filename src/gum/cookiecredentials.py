from socket import inet_aton
from struct import pack
from zope.app.authentication.interfaces import IAuthenticatorPlugin
from zope.app.authentication.interfaces import ICredentialsPlugin
from zope.app.authentication.session import SessionCredentialsPlugin
from zope.interface import Interface, implements
from zope.publisher.interfaces.http import IHTTPRequest
from zope.schema import ASCIILine
import base64, urllib
import binascii
import grok
import hashlib
import time
import urllib
import zope.app.authentication.principalfolder
import zope.session.interfaces

class ICookieCredentials(Interface):

    cookie_name = ASCIILine(
        title=(u'Cookie name'),
        description=(u'Name of the cookie for storing credentials.'),
        required=True
        )

class CookieCredentialsPlugin(SessionCredentialsPlugin):
    implements(ICookieCredentials)
    cookie_name = 'gum.auth'

    def extractCredentials(self, request):
        if not IHTTPRequest.providedBy(request):
            return

        login = request.get(self.loginfield, None)
        password = request.get(self.passwordfield, None)
        cookie = request.get(self.cookie_name, None)

        if login and password:
            val = base64.encodestring('%s:%s' % (login, password))
            request.response.setCookie(self.cookie_name,
                                       urllib.quote(val),
                                       path='/')
        elif cookie:
            val = base64.decodestring(urllib.unquote(cookie))
            login, password = val.split(':')
        else:
            return

        return {'login': login, 'password': password}

    def logout(self, request):
        request.response.expireCookie(self.cookie_name, path='/')

# mod_auth_tkt support

def createTicket(secret, userid, tokens=(), user_data=u'', ip='0.0.0.0', timestamp=None, encoding='utf8',):
    if timestamp is None:
        timestamp = int(time.time())

    userid = userid.encode(encoding)
    token_list = ','.join(tokens).encode(encoding)
    user_data = user_data.encode(encoding)

    # ip address is part of the format, set it to 0.0.0.0 to be ignored.
    # inet_aton packs the ip address into a 4 bytes in network byte order.
    # pack is used to convert timestamp from an unsigned integer to 4 bytes
    # in network byte order.
    data1 = inet_aton(ip) + pack("!I", timestamp)
    data2 = '\0'.join((userid, token_list, user_data))
    digest0 = hashlib.md5(data1 + str(secret) + data2).hexdigest()
    digest = hashlib.md5(digest0 + str(secret)).hexdigest()
    
    # digest + timestamp as an eight character hexadecimal + userid + !
    ticket = "%s%08x%s!" % (digest, timestamp, userid) 
    if tokens:
        ticket += token_list + '!'
    ticket += user_data

    return ticket

def splitTicket(ticket, encoding='utf8'):
    digest = ticket[:32]
    timestamp = int(ticket[32:40], 16) # convert from hexadecimal
    parts = ticket[40:].decode(encoding).split("!")

    if len(parts) == 2:
        userid, user_data = parts
        tokens = ()
    elif len(parts) == 3:
        userid, token_list, user_data = parts
        tokens = tuple(token_list.split(','))
    else:
        raise ValueError

    return (digest, userid, tokens, user_data, timestamp)


class TKTCookieCredentialsPlugin(SessionCredentialsPlugin):
    implements(ICookieCredentials)
    cookie_name = 'gum.auth'
    
    def extractCredentials(self, request):
        cookie_manager = zope.component.getUtility(
            zope.session.interfaces.IClientIdManager
        )
        cookie_credentials = zope.component.getUtility(
            ICredentialsPlugin, 'mod_auth_tkt',
        )
        try:
            ticket = request.cookies[cookie_credentials.cookie_name]
        except KeyError:
            return None
        ticket = urllib.unquote(ticket)
        credentials = binascii.a2b_base64(ticket).strip()
        # validate the credentials: people can have logged in with
        # a different cookie format and they will need to get a proper cookie
        try:
            data = splitTicket(credentials)
        except ValueError:
            return None
        return credentials
    
    def challenge(self, request):
        app = grok.getApplication()
        return request.response.redirect(app.login_url, trusted=True)
    
    def logout(self, request):
        request.response.expireCookie(cookie_credentials.cookie_name, path='/')


class TKTAuthenticatorPlugin(object):
    implements(IAuthenticatorPlugin)
    
    def authenticateCredentials(self, credentials):
        if not credentials:
            return None
        cookie_manager = zope.component.getUtility(
            zope.session.interfaces.IClientIdManager
        )
        
        (digest, userid, tokens, user_data, timestamp) = data = splitTicket(credentials)
        new_ticket = createTicket(
            cookie_manager.secret, userid, tokens, user_data,
            '0.0.0.0', timestamp, 'utf8')
        
        principal_info = zope.app.authentication.principalfolder.PrincipalInfo(
            u'gum.' + userid, userid, u'', u'')
        
        # To-Do: implement a cookie timeout feature
        if new_ticket[:32] == digest:
            return principal_info
    
    def principalInfo(self, id):
        pass
