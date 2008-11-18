import z3c.testsetup
from zope.app.testing.functional import getRootFolder
from gum.ldapapp import LDAPApp
from gum.ldapapp import Edit
from zope.app import zapi
from ldapadapter.interfaces import IManageableLDAPAdapter
from zope.app.authentication.interfaces import IAuthenticatorPlugin
from zope.app.security.interfaces import IAuthentication

LDAP_HOST = '127.0.0.1'
LDAP_PORT = '1700'
LDAP_LOGIN = 'cn=Manager,dc=example,dc=com'
LDAP_PASSWORD = 'secret'
LDAP_USER_SEARCH_BASE = 'ou=Webusers,dc=example,dc=com'
LDAP_GROUP_SEARCH_BASE = 'ou=Webgroups,ou=Groups,dc=example,dc=com'

def create_gum_instance(test):
    root = getRootFolder()
    root['gumsite'] = LDAPApp()
    root['gumsite'].ldap_admin_group = u'admin'
    root['gumsite'].ldap_view_group = u'viewer'
    from zope.app.component.hooks import setSite
    setSite(root['gumsite'])
    
    gumldapda = zapi.queryUtility(IManageableLDAPAdapter, 'gumldapda')
    auth = zapi.queryUtility(IAuthenticatorPlugin, 'ldap-authenticator')
    
    # update the LDAP Adapter
    gumldapda.host = LDAP_HOST
    gumldapda.port = LDAP_PORT
    gumldapda.useSSL = False
    gumldapda.bindDN = LDAP_LOGIN
    gumldapda.bindPassword = LDAP_PASSWORD
    
    # update the LDAP Authentication plugin
    auth.adapterName = 'gumldapda'
    auth.searchBase = LDAP_USER_SEARCH_BASE
    auth.searchScope = 'one'
    auth.groupsSearchBase = LDAP_GROUP_SEARCH_BASE
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

test_suite = z3c.testsetup.register_all_tests(
    'gum',
    setup=create_gum_instance,
    globs=dict(
        getRootFolder=getRootFolder,
    ),
)
