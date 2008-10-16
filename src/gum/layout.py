import grok
from zope.app import zapi
from zope.interface import Interface
from zope.app.security.interfaces import IAuthentication
from zope.app.security.interfaces import IUnauthenticatedPrincipal
from zope.securitypolicy.interfaces import IGrantInfo
from zope.app.interface import queryType
from zope.app.content.interfaces import IContentType
from gum.interfaces import IUser, IGroup, IOrganization
import grokcore.view

class Resources(grokcore.view.DirectoryResource):
    grokcore.view.name('resources')
    grokcore.view.path('resources')

class Layout(grok.View):
    "Shared layout for the application"
    grok.context(Interface)
    grok.name('layout')

class TopViewletManager(grok.ViewletManager):
    "Provide application logo and tabs for the top of the page"
    grok.name('top.gum')
    grok.context(Interface)

class TopViewlet(grok.Viewlet):
    grok.viewletmanager(TopViewletManager)
    grok.context(Interface)

    def nav(self):
        app = grok.getSite()
        
        return ( (app),
                 (app['users']),
                 (app['groups']),
                 (app['orgs']),
                 (app['transcripts']),
                 (app['smart']),
                )

class BottomViewletManager(grok.ViewletManager):
    "Provide footer elements"
    grok.name('bottom.gum')
    grok.context(Interface)

class BottomViewlet(grok.Viewlet):
    grok.viewletmanager(BottomViewletManager)
    grok.context(Interface)
    
    def app(self):
        return grok.getSite()
    
    def is_logged_in(self):
        if IUnauthenticatedPrincipal.providedBy(self.request.principal):
            return False
        else:
            return True
    
    def is_admin(self):
        grant_info = IGrantInfo( grok.getSite() )
        for role in grant_info.getRolesForPrincipal(self.request.principal.id):
            if role[0] == u'gum.Admin':
                return True
        return False

    def get_type_info(self):
        type_interface = queryType(self.context, IContentType)
        if not type_interface:
            return None
        return {'typename' : type_interface.getTaggedValue('typename'),
                'actions' : type_interface.getTaggedValue('actions') }
