from gum.cookiecredentials import TKTCookieCredentialsPlugin
from gum.cookiecredentials import TKTAuthenticatorPlugin
from gum.extensions import Extensions
from gum.interfaces import IOrganization
from gum.ldapapp import LDAPApp
from gum.organization import Organizations
from gum.smart import SmartSearches
from zope import interface
from zope.app import zapi
from zope.app.authentication.interfaces import ICredentialsPlugin
from zope.app.authentication.interfaces import IAuthenticatorPlugin
from zope.catalog.field import FieldIndex
from zope.catalog.interfaces import ICatalog
import grok
import grokcore.site.interfaces
import zope.component

class migrate04to05(object):
    def __init__(self, app):
        self.app = app
    
    def up(self):
        self.app.version = (0,5,0)
        
        orgs = Organizations()
        orgs.title = u'Organizations'
        self.app['orgs'] = orgs
        
        catalog = zapi.queryUtility(ICatalog, 'gum_catalog')
        catalog['organization_id'] = FieldIndex('__name__', IOrganization)
        
        return "Organizations Container added. organization_id Index added."


class migrate05to06(object):
    def __init__(self,app):
        self.app = app
    
    def up(self):
        self.app.version = (0,6,0)
        
        smrt = SmartSearches()
        smrt.title = u'Smart Searches'
        self.app['smart'] = smrt
        
        return "Smart Searches Container added."

class migrate06to08(object):
    def __init__(self, app):
        self.app = app
    
    def up(self):
        self.app.version = (0,8,0)
        
        ext = Extensions()
        ext.title = 'Extensions'
        self.app['extensions'] = ext
        
        return 'Extensions Container added.'

class migrate08to081(object):
    def __init__(self, app):
        self.app = app

    def up(self):
        self.app.version = (0,8,1)
        setup = zope.component.getUtility(grokcore.site.interfaces.IUtilityInstaller)
        setup(grok.getApplication(),
              TKTCookieCredentialsPlugin(),
              ICredentialsPlugin,
              name='mod_auth_tkt',
        )
        setup(grok.getApplication(),
              TKTAuthenticatorPlugin(),
              IAuthenticatorPlugin,
              name='tkt-auth',
        )

        return 'TKTCookieCredentials and TKTAuthenticator utilities installed.'

class VersionSetter(grok.View):
    grok.context(LDAPApp)
    grok.require(u'gum.View')
    
    def render(self):
        version = self.request.form.get('version', None)
        self.context.version = tuple([int(x) for x in version.split('.')])
        return 'Version set to %s' % str(self.context.version)

class upgradeApplication(grok.View):
    """
    Migrate the Schema to the latest version
    
    Right now this class is super cheesy simple.
    Since the primary data is stored in LDAP, we might
    not need that much in terms of migrations.
    """
    grok.context(LDAPApp)
    grok.name('upgrade')
    grok.require(u'gum.View')
    
    def update(self):
        if not hasattr(self.context, 'version'):
            self.context.version = (0,6,0)
    
    def render(self):
        if self.context.version == (0,4,2):
            migration = migrate04to05(app = self.context)
            results = migration.up()
            return "Application upgraded to %s.\n\n%s\n" % \
            ( '.'.join( [str(x) for x in self.context.version] ), results )
        elif self.context.version == (0,5,0):
            migration = migrate05to06(app = self.context)
            results = migration.up()
            return "Application upgraded to %s.\n\n%s\n" % \
            ( '.'.join( [str(x) for x in self.context.version] ), results )
        elif self.context.version == (0,6,0):
            migration = migrate06to08(app = self.context)
            results = migration.up()
            return "Application upgraded to %s.\n\n%s\n" % \
            ( '.'.join( [str(x) for x in self.context.version] ), results )
        elif self.context.version == (0,8,0):
            migration = migrate08to081(app = self.context)
            results = migration.up()
            return "Application upgraded to %s.\n\n%s\n" % \
            ( '.'.join( [str(x) for x in self.context.version] ), results )
        else:
            return "Application is already at the latest version: %s" % \
            ( '.'.join( [str(x) for x in self.context.version] ) )
