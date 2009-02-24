from gum import getPropertyAsSingleValue 
from gum.interfaces import IGroup 
from gum.widgets import AjaxUserChooserWidget 
from hurry import query 
from hurry.query.query import Query 
from zope import event 
from zope import interface, schema 
from zope.app.security.settings import Allow 
from zope.lifecycleevent import ObjectModifiedEvent 
from zope.securitypolicy.interfaces import IGrantInfo 
from zope.securitypolicy.interfaces import IPrincipalPermissionManager 
import grok 

class Groups(grok.Container):
    "Collection of Groups"

    def create_group_from_ldap_results(self, data):
        cn = getPropertyAsSingleValue( data, 'cn', u'' )
        description =  getPropertyAsSingleValue( data, 'description', u'' )
        # 'uniqueMember' looks like this:
        # [u'uid=kteague,ou=Testusers,dc=example,dc=com', u'uid=what,ou=Testusers,dc=example,dc=com']
        uids = []
        if data.has_key('uniqueMember'):
            for member in data['uniqueMember']:
                member = member.split(',')
                uids.append( member[0].split('=')[1] )
        uids = tuple(uids)
        return Group(cn, self, description, uids, exists_in_ldap=True) 
    
    def search(self, param, term, exact_match=True):
        "Search through groups and return matches as Group objects in a list"
        app = grok.getApplication()
        dbc = app.ldap_connection()
        
        if not exact_match:
            term = '*' + term + '*'
        
        results = dbc.search( app.ldap_group_search_base,
                              scope='one',
                              filter="(&(objectclass=groupOfUniqueNames)(%s=%s))"
                              % (param, term)
                            )
        groups = []
        for x in results:
            groups.append( self.create_group_from_ldap_results( x[1] ) )
        return groups

    def values(self):
        app = grok.getApplication()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_group_search_base,
                             scope='one',
                             filter="(&(objectclass=groupOfUniqueNames))" )
        groups = []
        for x in results:
            groups.append( self.create_group_from_ldap_results( x[1] ) )
        
        return groups
    
    def get(self, key, default=None):
        attr = getattr(self, key, None)
        if attr:
            return attr
        else:
            return self[key]
    
    def __getitem__(self, key):
        "Mapping between key (group cn) and LDAP-backed Group objects"
        app = grok.getApplication()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_group_search_base,
                              scope='one',
                              filter="(&(objectclass=groupOfUniqueNames)(cn=%s))"
                              % key
                            )
        if not results:
            raise KeyError, "Group id %s does not exist." % key
        else:
            return self.create_group_from_ldap_results(results[0][1])

    def __delitem__(self, key):
        "delete group"
        app = grok.getApplication()
        dbc = app.ldap_connection()
        dbc.delete( u"cn=%s,%s" % (key, app.ldap_group_search_base) )

    def searchGroupsByUser(self, uid):
        "Return all groups that a given uid belongs to"
        groups = []
        for group in self.values():
            if uid in group.uids:
                groups.append( group )
        
        return groups


class GroupsTraverser(grok.Traverser):
    """
    Grant security permissions during traversal.
    
    The "All Group Members are Managers" security permission:
    If you belong to a group, you can edit the group,
    including adding/removing people from the group.
    Future plan is to limit this permission to just the team 
    leads for a group.

    In addition, if you have the gum.Admin role, you can also
    edit groups. This is a somewhat slack permission, it should
    be constrained more in the future. The Transcripts feature should
    detect any naughty behaviour.
    """
    grok.context(Groups)
    
    def traverse(self, name):
        group = self.context[name]
        principal_id = self.request.principal.id
        uid = principal_id.split('.')[-1]
        
        # grant permissions if user belongs to group
        ppm = IPrincipalPermissionManager(grok.getApplication())     
        if uid in group.uids:
            ppm.grantPermissionToPrincipal(u'gum.EditGroup', principal_id)
        
        # grant permissions if the user is Admin
        grant_info = IGrantInfo(grok.getApplication())
        for role, perm in grant_info.getRolesForPrincipal(principal_id):
            if role == u'gum.Admin' and perm == Allow:
                ppm.grantPermissionToPrincipal(u'gum.EditGroup', principal_id)
        
        return group

class Group(grok.Model):
    "A single group of users"
    interface.implements(IGroup)
    
    def __init__(self, cn, container=None, description=u'', uids=[], exists_in_ldap=False):
        self.__name__ = cn
        self.__parent__ = container
        self.cn = cn
        self.description = description
        self.uids = uids
        self.exists_in_ldap = exists_in_ldap
    
    def save(self):
        "Store information in LDAP"
        app = grok.getApplication()
        dbc = app.ldap_connection()
        
        if not self.exists_in_ldap:
            dbc.add(self.dn, self.ldap_entry)
            self.exists_in_ldap = True
        else:
            dbc.modify(self.dn, self.ldap_entry)
    
    def load(self):
        "Fetch Group data from LDAP"
        app = grok.getApplication()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_group_search_base,
                              scope='one',
                              filter="(&(objectclass=groupOfUniqueNames)(cn=%s))" % self.cn )
        if not results:
            return None
        else:
            return results[0][1] 

    @property
    def title(self):
        return self.cn
        
    @property
    def dn(self):
        app = grok.getApplication()
        return u"cn=%s,%s" % (self.cn, app.ldap_group_search_base)

    @property
    def ldap_entry(self):
        "Representation of the object as an LDAP Entry"
        app = grok.getApplication()
        uniqueMembers = []
        for uid in self.uids:
            uniqueMembers.append( u'uid=%s,%s' % (uid, app.ldap_user_search_base))
        entry = { 'objectClass': ['top', 'groupOfUniqueNames'],
                  'cn': [ unicode(self.cn), ],
                  'uniqueMember': uniqueMembers, }
        if self.description:
            entry['description'] = [ unicode(self.description), ]
        return entry
    
    def users(self):
        "Users who belong to the Group"
        app = grok.getApplication()
        users = []
        return app['users'].search('uid', self.uids)

    def transcripts(self):
        "Transcript objects recording modifications made to this Group"
        transcripts = Query().searchResults(
            query.Eq( ('gum_catalog', 'dn'), self.dn )
            )
        return transcripts


class GroupsIndex(grok.View):
    "Default view for Groups"
    grok.context(Groups)
    grok.name('index')
    grok.require(u'gum.View')

class GroupIndex(grok.View):
    "View for a single Group"
    grok.context(Group)
    grok.name('index')
    grok.require(u'gum.View')

class GroupEdit(grok.EditForm):
    grok.context(Group)
    grok.name('editgroup')
    grok.require(u'gum.EditGroup')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    label = 'Edit Group'
    form_fields = grok.AutoFields(Group).omit('dn')
    form_fields['uids'].custom_widget = AjaxUserChooserWidget
    
    @grok.action('Save Changes')
    def edit(self, **data):
        # XXX validation hack
        # need to improve the validation and the UI experience
        app = grok.getApplication()
        try:
            for uid in data['uids']:
                app['users'][uid]
        except KeyError:
            pass
            # return "Uid %s does not exist.\nYou supplied the User Ids %s." % (uid, data['uids'])
        
        self.context.principal_id = self.request.principal.id # XXX oh the hackery!!!
        self.applyData(self.context, **data) # sends grok.ObjectModifedEvent
        self.context.save()
        self.redirect(self.url(self.context))


class DeleteGroup(grok.View):
    grok.context(Groups)
    grok.name('deletegroup')
    grok.require(u'gum.Edit')

    def render(self):
        id = self.request.form.get('id')
        group = self.context[ id ]
        group.principal_id = self.request.principal.id # XXX oh the hackery!!!
        event.notify( ObjectModifiedEvent(group) )
        del self.context[ id ]
        self.redirect(self.url(self.context))
