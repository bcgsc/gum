from zope import interface 
from zope.authentication.interfaces import IUnauthenticatedPrincipal 
from zope.publisher.browser import BrowserPage 
import grok 

class LoginPage(grok.View):
    grok.context(interface.Interface)
    grok.name('loginForm.html')
    grok.require('zope.Public')
    
    def __call__(self):
        request = self.request
        if (not IUnauthenticatedPrincipal.providedBy(request.principal)
            and 'gum.Login' in request):
            request.response.redirect( self.url(grok.getApplication()) )
        else:
            return self.template.render(self)
