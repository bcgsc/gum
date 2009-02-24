from gum.extensions import Extensions 
from gum.interfaces import IOrganization 
from gum.ldapapp import LDAPApp 
from gum.organization import Organizations 
from gum.smart import SmartSearches 
from zope import interface 
from zope.app import zapi 
from zope.app.catalog.field import FieldIndex 
from zope.app.catalog.interfaces import ICatalog 
import grok 

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
        else:
            return "Application is already at the latest version: %s" % \
            ( '.'.join( [str(x) for x in self.context.version] ) )