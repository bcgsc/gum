from gum.cookiecredentials import CookieCredentialsPlugin
from gum.extensions import Extensions
from gum.group import Groups, Group
from gum.interfaces import IGroup
from gum.interfaces import ILDAPUserGroupLocation
from gum.interfaces import ITranscript, IOrganization
from gum.organization import Organizations
from gum.smart import SmartSearches
from gum.transcript import Transcripts
from gum.user import Users, User
from gum.user import core_user_fields
from ldapadapter.interfaces import IManageableLDAPAdapter
from ldapadapter.utility import ManageableLDAPAdapter
from zope import component
from zope.app import authentication
from zope.app import zapi
from zope.app.authentication.interfaces import IAuthenticatorPlugin
from zope.app.authentication.interfaces import ICredentialsPlugin
from zope.app.authentication.interfaces import IPrincipalCreated
from zope.app.catalog.catalog import Catalog
from zope.app.catalog.field import FieldIndex
from zope.app.catalog.interfaces import ICatalog
from zope.app.intid import IntIds
from zope.app.intid.interfaces import IIntIds
from zope.app.security.interfaces import IAuthentication
from zope.event import notify
from zope.interface import implements
from zope.lifecycleevent import ObjectCreatedEvent
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager
from zope.securitypolicy.interfaces import Unset, Allow
import grok
import ldap
import ldappas.authentication
import zope.securitypolicy.interfaces

def setup_catalog(catalog):
    "Configure Indexes upon catalog creation"
    catalog['dn'] = FieldIndex('dn', ITranscript)
    catalog['principal_id'] = FieldIndex('principal_id', ITranscript)
    catalog['observation_datetime'] = \
        FieldIndex('observation_datetime', ITranscript)
    catalog['organization_id'] = FieldIndex('id', IOrganization)


class LDAPApp(grok.Application, grok.Container):
    "Root application object for the gum app"
    implements(ILDAPUserGroupLocation)
    ldap_admin_group = u''
    ldap_view_group = u''
    
    # GUM does it's Authentication againast LDAP
    # using the Pluggable Authentication Utility (PAU)
    # PAU works by requiring a set of:
    # * credentials plugins for determining how to extract the creds 
    #   (username/password)
    # * authenitcation plugins for determining if the creds are valid
    # we are just going to use a single cookie creds plugin and a
    # ldap auth plugin
    grok.local_utility( authentication.PluggableAuthentication,
                        provides=IAuthentication, )
    grok.local_utility( ldappas.authentication.LDAPAuthentication,
                        provides=IAuthenticatorPlugin,
                        name='ldap-authenticator' )
    grok.local_utility( CookieCredentialsPlugin,
                        provides=ICredentialsPlugin,
                        name='gum-creds' )
    
    # The 'gumldapda' is a named utility that acts as a database adapter
    # in Zope 3 a connection to ldap is treated like a connection to
    # any other database, e.g. a relation database adatper for example
    grok.local_utility( ManageableLDAPAdapter,
                        provides=IManageableLDAPAdapter,
                        name='gumldapda' )
    
    # Utilities to catalog the transcripts
    grok.local_utility(IntIds, provides=IIntIds)
    grok.local_utility(Catalog, provides=ICatalog, name='gum_catalog',
                       setup=setup_catalog)
    
    def __init__(self):
        super(LDAPApp, self).__init__()
        self.title = 'Home' # for navigation
        self['groups'] = Groups()
        self['groups'].title = 'Groups'
        self['users'] = Users()
        self['users'].title = 'Users'
        self['transcripts'] = Transcripts()
        self['transcripts'].title = 'Transcripts'
        self['orgs'] = Organizations()
        self['orgs'].title = 'Organizations'
        self['smart'] = SmartSearches()
        self['smart'].title = 'Smart Searches'
        self['extensions'] = Extensions()
        self['extensions'].title = 'Extensions'
    
    def ldap_connection(self):
        "LDAP connection"
        return zapi.queryUtility(IManageableLDAPAdapter, 'gumldapda').connect()
    
    # GUM LDAP settings, these are pulled from the configured
    # LDAP adapter and LDAP authenticator objects in PAU
    
    @property
    def ldap_host(self):
        return zapi.queryUtility(IManageableLDAPAdapter,'gumldapda').host
    
    @property
    def ldap_port(self):
        return zapi.queryUtility(IManageableLDAPAdapter,'gumldapda').port
    
    @property
    def ldap_login(self):
        return zapi.queryUtility(IManageableLDAPAdapter,'gumldapda').bindDN
    
    @property
    def ldap_password(self):
        return zapi.queryUtility(
            IManageableLDAPAdapter,'gumldapda').bindPassword
    
    @property
    def ldap_user_search_base(self):
        return zapi.queryUtility(
            IAuthenticatorPlugin, 'ldap-authenticator').searchBase
    
    @property
    def ldap_group_search_base(self):
        return zapi.queryUtility(
            IAuthenticatorPlugin, 'ldap-authenticator').groupsSearchBase


class Index(grok.View):
    "Default view for the gum app"
    grok.context(LDAPApp)
    grok.name('index')
    grok.require(u'gum.View')

class Edit(grok.EditForm):
    "Form to edit GUM global configuration"
    grok.context(LDAPApp)
    grok.name('edit')
    grok.require('zope.Manager')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    @grok.action('Save changes')
    def edit(self, **data):
        gumldapda = zapi.queryUtility(IManageableLDAPAdapter,'gumldapda')
        auth = zapi.queryUtility(IAuthenticatorPlugin, 'ldap-authenticator')
        
        # update the LDAP Adapter
        gumldapda.host = data['ldap_host']
        gumldapda.port = data['ldap_port']
        gumldapda.useSSL = False
        gumldapda.bindDN = data['ldap_login']
        gumldapda.bindPassword = data['ldap_password']
        
        # update the LDAP Authentication plugin
        auth.adapterName = 'gumldapda'
        auth.searchBase = data['ldap_user_search_base']
        auth.searchScope = 'one'
        auth.groupsSearchBase = data['ldap_group_search_base']
        auth.groupsSearchScope = 'one'
        auth.loginAttribute = 'uid'
        auth.principalIdPrefix = u'ldap.'
        auth.idAttribute = 'uid'
        auth.titleAttribute = 'sn'
        auth.groupsAttribute = 'ou'
        auth.groupIdAttribute = 'cn'
        
        # register the creds and auth plug-ins with the PAU
        pau = zapi.queryUtility(IAuthentication)
        pau.credentialsPlugins = ('gum-creds',)
        pau.authenticatorPlugins = ('ldap-authenticator', )
        pau.prefix = u'gum.'
        
        # update the app
        self.context.ldap_admin_group = data['ldap_admin_group']
        self.context.ldap_view_group = data['ldap_view_group']
        sync_ldap_perms(self.context)
        
        self.redirect(self.url(self.context))

@grok.subscribe(IPrincipalCreated)
def update_principal_info_from_ldap(event):
    "Update the principal with information from LDAP"
    principal = event.principal
    app = grok.getApplication()
    __name__ = principal.id.split('.')[-1]
    user = app['users'][__name__]
    principal.title = user.cn
    principal.__name__ = __name__

@grok.subscribe(grok.interfaces.IApplication, grok.IObjectAddedEvent)
def grant_roles_to_permissions(obj, event):
    # grant roles to permissions
    rpm = IRolePermissionManager(obj)
    rpm.grantPermissionToRole(u'gum.Add', u'gum.Admin')
    rpm.grantPermissionToRole(u'gum.Edit', u'gum.Admin')

class LDAPPrincipalPermissionMap(grok.Adapter):
    grok.context(LDAPApp)
    grok.provides(zope.securitypolicy.interfaces.IPrincipalPermissionMap)
    
    def getPrincipalsForPermission(permission_id):
        # not needed ATM
        return None

    def getPermissionsForPrincipal(principal_id):
        # not needed ATM
        return None

    def getPrincipalsAndPermissions():
        # not needed ATM
        return None
    
    def getSetting(self, permission_id, principal_id, default=Unset):
        name = principal_id.split('.')[-1]
        
        # View permission
        if permission_id == u'gum.View':
            if name in self.context['groups'][self.context.ldap_view_group].uids:
                return Allow

        # Add/Edit/EditGroup permissions
        if name in self.context['groups'][self.context.ldap_admin_group].uids:
            return Allow
        return Unset

class CleanOldPerms(grok.View):
    "Migrate away from ZODB stored permissions"
    grok.context(LDAPApp)
    grok.require(u'gum.View')
    
    def render(self):
        app = grok.getApplication()
        prm = IPrincipalRoleManager(app)
        ppm = IPrincipalPermissionManager(app)
        for p in ppm.getPrincipalsAndPermissions():
            ppm.unsetPermissionForPrincipal(u'gum.View', p[1])
        for p in prm.getPrincipalsAndRoles():
            prm.unsetRoleForPrincipal(u'gum.Admin', p[1])
        return 'The deed has been done.'

#
# User related Views
#
class AddUser(grok.AddForm):
    grok.context(LDAPApp)
    grok.name('adduser')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = core_user_fields()
    form_fields = form_fields.select( 'cn',
                                      'sn',
                                      'givenName',
                                      '__name__',
                                      'email',
                                      'telephoneNumber',
                                      'description',
                                      'o',
                                    )
    label = "Add User"
    
    @grok.action('Add User entry')
    def add(self, **data):
        users = self.context['users']
        __name__ = data['__name__']
        del data['__name__']
        user = User(__name__, container=users, **data)
        user.principal_id = self.request.principal.id # XXX oh the hackery!!!
        notify( ObjectCreatedEvent(user) )
        user.save()
        self.redirect(self.url(users[__name__]))


class SearchUsers(grok.View):
    "Search Results"
    grok.context(LDAPApp)
    grok.name('searchusers')
    grok.require(u'gum.View')

    def results(self):
        search_param = ldap.filter.escape_filter_chars(
            self.request.form.get('search_param')
        )
        search_term = ldap.filter.escape_filter_chars(
            self.request.form.get('search_term')
        )
        exact_match = self.request.form.get('exact_match', False)
        if not search_term: return []
        
        return self.context['users'].search(
            search_param,
            search_term,
            exact_match,
        )


class SimpleUserSearch(grok.View):
    """
    Simplified search results which searches on the
    Canonical Name, User Id and Email fields
    """
    grok.context(LDAPApp)
    grok.name('simpleusersearch')
    grok.template('searchusers')
    grok.require(u'gum.View')

    def results(self):
        search_term = ldap.filter.escape_filter_chars(
            self.request.form.get('search_term')
        )
        if not search_term: return []
        
        users = self.context['users']
        results = {}
        
        # search the Canonical Name (cn)
        for user in users.search('cn', search_term, False):
            results[user.__name__] = user
        
        # search the User Id (uid)
        for user in users.search('uid', search_term, False):
            results[user.__name__] = user
        
        # search the Email (email)
        for user in users.search('mail', search_term, False):
            results[user.__name__] = user
        
        return results.values()


class AutoCompleteSearch(grok.View):
    "It's AJAXy!"
    grok.context(LDAPApp)
    grok.name('autocompletesearch')
    grok.require(u'gum.View')

    def render(self):
        search_term = ldap.filter.escape_filter_chars(
            self.request.form.get('search_term', None)
        )
        if not search_term or len(search_term) < 3:
            return ""

        users = self.context['users']
        results = {}
        # search the Canonical Name (cn)
        for user in users.search('cn', search_term, False):
            results[user.__name__] = user

        # search the User Id (uid)
        for user in users.search('uid', search_term, False):
            results[user.__name__] = user

        # search the Email (email)
        for user in users.search('mail', search_term, False):
            results[user.__name__] = user

        if not results:
            return ""

        out = "<ul>"
        for user in results.values()[:15]:
            out += '<li><a href="%s">%s</a></li>' % (
                self.url(user), user.cn
            )
        if len(results.values()) > 15:
            out += '<li>More results ...</li>'
        out += "</ul>"
        
        return out


class AutoCompleteSearchUidAddable(grok.View):
    "It's AJAXy! part 2"
    # XXX To-do:
    # - move search into a single LDAP query
    grok.context(LDAPApp)
    grok.name('autocompletesearchuidaddable')
    grok.require(u'gum.View')

    def users(self):
        search_term = ldap.filter.escape_filter_chars(
            self.request.form.get('search_term', None)
        )
        if not search_term or len(search_term) < 3:
            return {}

        users = self.context['users']
        results = {}
        
        # search the Canonical Name (cn)
        for user in users.search('cn', search_term, False):
            results[user.__name__] = user

        # search the User Id (uid)
        for user in users.search('uid', search_term, False):
            results[user.__name__] = user

        # search the Email (email)
        for user in users.search('mail', search_term, False):
            results[user.__name__] = user

        return results.values()[:15]

#
# Group related Views
#

class AddGroup(grok.AddForm):
    grok.context(LDAPApp)
    grok.name('addgroup')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.AutoFields(Group).omit('dn','title')
    label = "Add Group"
    
    @grok.action('Add Group entry')
    def add(self, **data):
        gid = data['cn']
        groups = self.context['groups']
        group = Group(
            gid,
            groups,
            description=data['description'],
            uids=data['uids'],
            exists_in_ldap=False,)
        group.principal_id = self.request.principal.id # XXX oh the hackery!!!
        notify(ObjectCreatedEvent(group))
        group.save()
        self.redirect(self.url(group))

#
# XML-RPC Web Service API
#

class GUMRPC(grok.XMLRPC):
    "Simple way of fetching user and group information"
    grok.context(LDAPApp)
    
    def get_group_info_by_id(self, group_id):
        "Return dictionary of group info given a valid group id"
        group = self.context['groups'][group_id]
        group_info = {}
        group_info['title'] = group.title
        group_info['description'] = group.description
        group_info['uids'] = group.uids
        return group_info
    
    def get_user_info_by_id( self, user_id ):
        "Return dictionary of user info given a valid user id"
        try:
            user = self.context['users'][user_id]
        except KeyError:
            return {'telephoneNumber': [], 'cn': '', 'email': ''}
        user_info = {}
        user_info['cn'] = user.cn
        user_info['email'] = user.email
        user_info['telephoneNumber'] = user.telephoneNumber
        return user_info
