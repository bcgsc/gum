import base64, urllib
from zope.interface import Interface, implements
from zope.schema import ASCIILine
from zope.publisher.interfaces.http import IHTTPRequest
from zope.app.authentication.session import SessionCredentialsPlugin

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
        if not IHTTPRequest.providedBy(request):
            return
        request.response.expireCookie(self.cookie_name, path='/')
