from gum.cookiecredentials import CookieCredentialsPlugin
from gum.cookiecredentials import TKTAuthenticatorPlugin
from gum.cookiecredentials import TKTCookieCredentialsPlugin
from gum.extensions import Extensions
from gum.group import Groups, Group
from gum.interfaces import ICookieConfiguration
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
from zope.authentication.interfaces import IAuthentication
from zope.catalog.catalog import Catalog
from zope.catalog.field import FieldIndex
from zope.catalog.interfaces import ICatalog
from zope.event import notify
from zope.interface import implements
from zope.intid import IntIds
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import ObjectCreatedEvent
from zope.pluggableauth.interfaces import IAuthenticatorPlugin
from zope.pluggableauth.interfaces import ICredentialsPlugin
from zope.pluggableauth.interfaces import IPrincipalCreated
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IRolePermissionManager
from zope.securitypolicy.interfaces import Unset, Allow
import datetime
import grok
import grokcore.site
import ldap
import ldapadapter.interfaces
import ldappas.authentication
import zope.component
import zope.pluggableauth
import zope.securitypolicy.interfaces
import zope.session.interfaces

def setup_catalog(catalog):
    "Configure Indexes upon catalog creation"
    catalog['dn'] = FieldIndex('dn', ITranscript)
    catalog['principal_id'] = FieldIndex('principal_id', ITranscript)
    catalog['observation_datetime'] = \
        FieldIndex('observation_datetime', ITranscript)
    catalog['organization_id'] = FieldIndex('id', IOrganization)


class LDAPApp(grok.Application, grok.Container):
    "Root application object for the gum app"
    implements(ILDAPUserGroupLocation, ICookieConfiguration)
    ldap_admin_group = u''
    ldap_sysadmin_group = u''
    ldap_view_group = u''
    cookie_name = u'gum'
    shared_secret = u''
    enable_mod_auth_tkt = False
    login_url = u''
    
    # GUM does it's Authentication againast LDAP
    # using the Pluggable Authentication Utility (PAU)
    # PAU works by requiring a set of:
    # * credentials plugins for determining how to extract the creds 
    #   (username/password)
    # * authenitcation plugins for determining if the creds are valid
    # we are just going to use a single cookie creds plugin and a
    # ldap auth plugin
    grok.local_utility( zope.pluggableauth.authentication.PluggableAuthentication,
                        provides=IAuthentication, )
    grok.local_utility( ldappas.authentication.LDAPAuthentication,
                        provides=IAuthenticatorPlugin,
                        name='ldap-authenticator' )
    grok.local_utility( CookieCredentialsPlugin,
                        provides=ICredentialsPlugin,
                        name='gum-creds' )
    grok.local_utility( TKTCookieCredentialsPlugin,
                        provides=ICredentialsPlugin,
                        name='mod_auth_tkt' )
    grok.local_utility( TKTAuthenticatorPlugin,
                        provides=IAuthenticatorPlugin,
                        name='tkt-auth' )
    
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
        return zope.component.queryUtility(IManageableLDAPAdapter, 'gumldapda').connect()
    
    # GUM LDAP settings, these are pulled from the configured
    # LDAP adapter and LDAP authenticator objects in PAU
    
    @property
    def ldap_host(self):
        return zope.component.queryUtility(IManageableLDAPAdapter,'gumldapda').host
    
    @property
    def ldap_port(self):
        return zope.component.queryUtility(IManageableLDAPAdapter,'gumldapda').port
    
    @property
    def ldap_login(self):
        return zope.component.queryUtility(IManageableLDAPAdapter,'gumldapda').bindDN
    
    @property
    def ldap_password(self):
        return zope.component.queryUtility(
            IManageableLDAPAdapter,'gumldapda').bindPassword
    
    @property
    def ldap_user_search_base(self):
        return zope.component.queryUtility(
            IAuthenticatorPlugin, 'ldap-authenticator').searchBase
    
    @property
    def ldap_group_search_base(self):
        return zope.component.queryUtility(
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
        gumldapda = zope.component.queryUtility(IManageableLDAPAdapter,'gumldapda')
        auth = zope.component.queryUtility(IAuthenticatorPlugin, 'ldap-authenticator')
        
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
        pau = zope.component.queryUtility(IAuthentication)
        pau.authenticatorPlugins = ('ldap-authenticator', )
        pau.prefix = u'gum.'
        
        # update the app
        self.context.ldap_admin_group = data['ldap_admin_group']
        self.context.ldap_sysadmin_group = data['ldap_sysadmin_group']
        self.context.ldap_view_group = data['ldap_view_group']
        
        # update the session settings
        self.context.login_url = data['login_url']
        self.context.shared_secret = data['shared_secret']
        self.context.cookie_name = data['cookie_name']
        self.context.enable_mod_auth_tkt = data['enable_mod_auth_tkt']
        cookie_manager = zope.component.getUtility(
            zope.session.interfaces.IClientIdManager
        )
        if data['enable_mod_auth_tkt']:
            cookie_manager.thirdparty = True
            cookie_manager.secret = data['shared_secret']
            cookie_credentials = zope.component.getUtility(
                ICredentialsPlugin, 'mod_auth_tkt',
            )
            cookie_credentials.cookie_name = data['cookie_name']
            pau.credentialsPlugins = ('mod_auth_tkt','gum-creds',)
            pau.authenticatorPlugins = ('tkt-auth','ldap-authenticator',)
        else:
            cookie_manager.thirdparty = False
            cookie_credentials = zope.component.getUtility(
                ICredentialsPlugin, 'gum-creds',
            )
            cookie_credentials.cookie_name = data['cookie_name']
            pau.credentialsPlugins = ('gum-creds',)
            pau.authenticatorPlugins = ('ldap-authenticator',)
        
        self.redirect(self.url(self.context))

class ResetSessionSettings(grok.View):
    """
    Session settings are global, but PAU settings are local,
    so we need to disable mod_auth_tkt in order to use the Grok admin UI.
    """
    grok.name('reset')
    grok.context(zope.interface.Interface)
    
    def render(self):
        cookie_manager = zope.component.getUtility(
            zope.session.interfaces.IClientIdManager
        )
        cookie_manager.thirdparty = False
        cookie_manager.secret = ''
        return 'Reset to normal cookie login'

@grok.subscribe(IPrincipalCreated)
def update_principal_info_from_ldap(event):
    "Update the principal with information from LDAP"
    principal = event.principal
    app = grok.getApplication()
    __name__ = principal.id.split('.')[-1]
    user = app['users'][__name__]
    principal.title = user.cn
    principal.__name__ = __name__

@grok.subscribe(grokcore.site.interfaces.IApplication, grok.IObjectAddedEvent)
def grant_roles_to_permissions(obj, event):
    # grant roles to permissions
    rpm = IRolePermissionManager(obj)
    rpm.grantPermissionToRole(u'gum.Add', u'gum.Admin')
    rpm.grantPermissionToRole(u'gum.Edit', u'gum.Admin')

class LDAPGrantInfo(grok.Adapter):
    grok.context(LDAPApp)
    grok.provides(zope.securitypolicy.interfaces.IGrantInfo)
    
    def principalPermissionGrant(self, principal, permission): return None
    def getRolesForPermission(self, permission): return None
    def getRolesForPrincipal(self, principal):
        # bootstrapper-y: an unconfigured application must allow access
        free_pass = [ (u'gum.View', Allow), (u'gum.Admin', Allow), ]
        if not self.context.ldap_view_group or not self.context.ldap_admin_group:
            return free_pass

        name = principal.split('.')[-1]
        roles = []
        
        try:
            if name in self.context['groups'][self.context.ldap_view_group].uids:
                roles.append( (u'gum.View', Allow) )
            if name in self.context['groups'][self.context.ldap_admin_group].uids:
                roles.append( (u'gum.Admin', Allow) )
            if name in self.context['groups'][self.context.ldap_sysadmin_group].uids:
                roles.append( (u'gum.SysAdmin', Allow) )
        except ldapadapter.interfaces.NoSuchObject, ldapadapter.interfaces.InvalidCredentials:
            return free_pass
        
        return roles

class LDAPPrincipalPermissionMap(grok.Adapter):
    grok.context(LDAPApp)
    grok.provides(zope.securitypolicy.interfaces.IPrincipalPermissionMap)
    
    def getPrincipalsForPermission(permission_id): return None
    def getPermissionsForPrincipal(principal_id): return None
    def getPrincipalsAndPermissions(): return None
    
    def getSetting(self, permission_id, principal_id, default=Unset):
        
        # bootstrapper-y: an unconfigured application must allow access
        if not self.context.ldap_view_group or not self.context.ldap_admin_group:
            return Allow
        
        # Allow access if the LDAP server is down
        try:
            view_group_names = self.context['groups'][self.context.ldap_view_group].uids
            admin_group_names = self.context['groups'][self.context.ldap_admin_group].uids
            sysadmin_group_names = self.context['groups'][self.context.ldap_sysadmin_group].uids
        except ldapadapter.interfaces.ServerDown:
            return Allow
        
        name = principal_id.split('.')[-1]
        
        # View permission
        if permission_id == u'gum.View':
            try:
                if name in self.context['groups'][self.context.ldap_view_group].uids:
                    return Allow
            except ldapadapter.interfaces.NoSuchObject, ldapadapter.interfaces.InvalidCredentials:
                return Allow
        
        # Add/Edit/EditGroup permissions
        if permission_id in [u'gum.Add', u'gum.Edit', u'gum.EditGroup',]:
            try:
                if name in self.context['groups'][self.context.ldap_admin_group].uids:
                    return Allow
            except ldapadapter.interfaces.NoSuchObject, ldapadapter.interfaces.InvalidCredentials:
                return Allow

        # SysAdmin level permissions
        try:
            if name in self.context['groups'][self.context.ldap_sysadmin_group].uids:
                return Allow
        except ldapadapter.interfaces.NoSuchObject, ldapadapter.interfaces.InvalidCredentials:
            return Allow
        
        return Unset

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

        return results.values()[:15]

#
# Group related Views
#

def check_for_whitespace(form, action, data):
    # do not allow the Space character in the name
    # some applications do not work with groups with this character (e.g. Confluence)
    if form.widgets['cn'].getInputValue().find(' ') != -1:
        from zope.formlib.interfaces import WidgetInputError
        return [
            WidgetInputError(
                field_name='cn',
                widget_title=(u'Common Name'),
                errors=(u'Spaces are not allowed in the name.'),
            )
        ]
    # to-do: I do not know why we manually copy the data from the form
    # but it is necessary to make this work ...
    data['cn'] = form.widgets['cn'].getInputValue()
    data['description'] = form.widgets['description'].getInputValue()
    data['uids'] = form.widgets['uids'].getInputValue()
    
    return []

    
class AddGroup(grok.AddForm):
    grok.context(LDAPApp)
    grok.name('addgroup')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.AutoFields(Group).omit('dn','title')
    label = "Add Group"
    
    @grok.action('Add Group entry', validator=check_for_whitespace,)
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
    
    def _marshall_user_info(self, user):
        user_info = {}
        user_info['__name__'] = user.__name__
        user_info['cn'] = user.cn
        user_info['sn'] = user.sn
        user_info['givenName'] = user.givenName
        user_info['email'] = user.email
        user_info['telephoneNumber'] = user.telephoneNumber
        user_info['street'] = user.street
        user_info['roomNumber'] = user.roomNumber
        user_info['description'] = user.description
        user_info['job_title'] = user.job_title
        user_info['ou'] = user.ou
        user_info['employeeType'] = user.employeeType
        user_info['o'] = user.o
        user_info['labeledUri'] = user.labeledUri
        return user_info

    def search(self, search_term):
        "Search for users and return matches (15 max)"
        search_term = ldap.filter.escape_filter_chars(
            search_term
        )
        if not search_term or len(search_term) < 3:
            return []
        users = self.context['users']
        results = {}
        
        # search the Canonical Name (cn)
        for user in users.search('cn', search_term, False):
            results[user.__name__] = user.cn
        # search the User Id (uid)
        for user in users.search('uid', search_term, False):
            results[user.__name__] = user.cn
        # search the Email (email)
        for user in users.search('mail', search_term, False):
            results[user.__name__] = user.cn
        
        return [
            {'uid':uid,'name':name} for uid,name in results.items()
        ][:15]
    
    def get_group_info_by_id(self, group_id):
        "Return dictionary of group info given a valid group id"
        group = self.context['groups'][group_id]
        group_info = {}
        group_info['title'] = group.title
        group_info['description'] = group.description
        group_info['uids'] = group.uids
        return group_info
    
    def get_user_info_by_id(self, user_id ):
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

    def all_users(self):
        "All users info"
        out = []
        users = grok.getApplication()['users']
        for user in users.values():
            out.append(self._marshall_user_info(user))
        return out
    
    def recent_modifications(self, days=30):
        """
        User info for any user modified in the last 30 days
        """
        users = {}
        app = grok.getApplication()
        for mod in self.context['transcripts'].sorted_by_date():
            now = datetime.datetime.now()
            if now - datetime.timedelta(days) < mod.observation_datetime:            
                name = mod.dn.split(',')[0].split('=')[1]
                try:
                    user = app['users'][name]
                    users[user.__name__] = self._marshall_user_info(user)
                    users[user.__name__]['modified'] = mod.observation_datetime
                except KeyError:
                    pass
        return users.values()

    def create_user(self,
        username,
        email,
        password='****',
        cn='Created with GUM API',
        sn='Created with GUM API',
        givenName='Created with GUM API',
        telephoneNumber='',
        description='',
        o='',):
        "Create a new user account"
        users = self.context['users']
        user = User(
            username,
            container=users,
            cn=cn,
            sn=sn,
            givenName=givenName,
            email=email,
            telephoneNumber=telephoneNumber,
            description=description,
            o=o,
        )
        user.principal_id = self.request.principal.id # XXX oh the hackery!!!
        notify( ObjectCreatedEvent(user) )
        users[username] = user
        user.changePassword(password, password)
        user.save()
        
        return True

