import grok
from zope import interface
from zope.publisher.browser import BrowserPage
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.security.interfaces import IUnauthenticatedPrincipal

class LoginPage(grok.View):
    grok.context(interface.Interface)
    grok.name('loginForm.html')
    
    def __call__(self):
        request = self.request
        if (not IUnauthenticatedPrincipal.providedBy(request.principal)
            and 'gum.Login' in request):
            request.response.redirect( self.url(grok.getSite()) )
        else:
            return self.template.render(self)
