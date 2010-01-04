import gum.ldapapp
import ldapadapter.interfaces
import os.path
import z3c.testsetup
import zope.app.authentication.interfaces
import zope.app.security.interfaces
import zope.app.testing.functional
import zope.component
import zope.site.hooks

LDAP_HOST = '127.0.0.1'
LDAP_PORT = '1700'
LDAP_LOGIN = 'cn=Manager,dc=example,dc=com'
LDAP_PASSWORD = 'secret'
LDAP_USER_SEARCH_BASE = 'ou=Webusers,dc=example,dc=com'
LDAP_GROUP_SEARCH_BASE = 'ou=Webgroups,ou=Groups,dc=example,dc=com'

def create_gum_instance(test):
    root = zope.app.testing.functional.getRootFolder()
    root['gumsite'] = gum.ldapapp.LDAPApp()
    root['gumsite'].ldap_admin_group = u'admin'
    root['gumsite'].ldap_view_group = u'admin'
    zope.site.hooks.setSite(root['gumsite'])
    
    gumldapda = zope.component.queryUtility(
        ldapadapter.interfaces.IManageableLDAPAdapter,
        'gumldapda',
    )
    auth = zope.component.queryUtility(
        zope.app.authentication.interfaces.IAuthenticatorPlugin,
        'ldap-authenticator',
    )
    
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
    pau = zope.component.queryUtility(zope.app.security.interfaces.IAuthentication)
    pau.credentialsPlugins = ('gum-creds',)
    pau.authenticatorPlugins = ('ldap-authenticator', )
    pau.prefix = u'gum.'

ftesting_zcml = os.path.join(os.path.dirname(gum.__file__), 'ftesting.zcml')
FunctionalLayer = zope.app.testing.functional.ZCMLLayer(
    ftesting_zcml, __name__,
    'FunctionalLayer',
    allow_teardown=True
)
                            
test_suite = z3c.testsetup.register_all_tests(
    'gum',
    setup=create_gum_instance,
)
