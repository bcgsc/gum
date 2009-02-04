import grok
from urllib import urlencode
from zope import schema, interface
from zope import component
from zope import event
from zope.formlib.form import FormFields
from hurry.query.query import Query
from hurry import query
import ldap
from ldap.modlist import addModlist, modifyModlist
import SSHA
from gum.interfaces import IUser, IUsers, IUserSchemaExtension, IINetOrgPerson
from gum import decombobulate

def core_user_fields():
    "List of built-in User schema fields"
    return grok.Fields(IINetOrgPerson)

def additional_user_fields():
    "List of fields that the User schema has been extended with"
    fields = []
    for ext in component.getUtilitiesFor(IUserSchemaExtension):
        for field in ext[1].fields:
            if not field.__name__ == 'objectClass':
                fields.append(field)
    return FormFields(*fields)

class Users(grok.Container):
    "Collection of Users"
    interface.implements(IUsers)
    
    def create_user_from_ldap_results(self, data):
        userdata = {
            'container' : self,
            'exists_in_ldap' : True,
        }
        fields = core_user_fields() + additional_user_fields()
        fields = fields.omit('dn','uid')
        for field in fields:
            userdata[field.__name__] = decombobulate(field.field, data)
        return User(
            data['uid'][0],
            **userdata
        )
    
    def search(self, param, term, exact_match=True):
        "Search through users and return matches as User objects in a list"
        app = grok.getSite()
        dbc = app.ldap_connection()
        
        if not exact_match:
            term = '*' + term + '*'
        
        if type(term) == type([]) or type(term) == type((),):
            filter_ext = "(|"
            for item in term:
                filter_ext += "(%s=%s)" % (param, item)
            filter_ext += ")"
        else:
            filter_ext = "(%s=%s)" % (param, term)
        results = dbc.search( app.ldap_user_search_base,
                              scope='one',
                              filter="(&(objectclass=inetOrgPerson)%s)"
                              % filter_ext
                            )
        users = []
        for x in results:
            users.append( self.create_user_from_ldap_results(x[1]) )
        return users
    
    def search_count(self, param, term):
        "Search through users, but only return a count of matches"
        app = grok.getSite()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_user_search_base,
                              scope='one',
                              filter="(&(objectclass=inetOrgPerson)(%s=%s))"
                              % (param, term) )
        return len(results)
    
    def orgsearch(self,
                  search_criteria,
                  ):
        "Search through users by organizational criteria"
        # the normal user.search() could be generalized to handle this search
        # but constructing LDAP searches can get rather hairy ...
        app = grok.getSite()
        dbc = app.ldap_connection()
        
        org_sub_filter = ''
        if search_criteria.organizations:
            org_sub_filter += '(|'
            for org in search_criteria.organizations:
                org_sub_filter += '(o=%s)' % org
            org_sub_filter += ')'
        
        street_sub_filter = ''
        if search_criteria.streets:
            street_sub_filter += '(|'
            for street in search_criteria.streets:
                street_sub_filter += '(street=%s)' % street
            street_sub_filter += ')'
        
        emp_sub_filter = ''
        if search_criteria.employeeTypes:
            emp_sub_filter += '(|'
            for employeeType in search_criteria.employeeTypes:
                emp_sub_filter += '(employeeType=%s)' % employeeType
            emp_sub_filter += ')'
        
        orgunit_sub_filter = ''
        if search_criteria.orgunitTypes:
            orgunit_sub_filter += '(|'
            for orgunitType in search_criteria.orgunitTypes:
                orgunit_sub_filter += '(ou=%s)' % orgunitType
            orgunit_sub_filter += ')'
        
        filter_str = '(&(objectclass=inetOrgPerson)%s%s%s%s)' % (
            org_sub_filter,
            street_sub_filter,
            emp_sub_filter,
            orgunit_sub_filter
        )
        results = dbc.search( app.ldap_user_search_base,
                              scope='one',
                              filter=filter_str )
        users = []
        for x in results:
            users.append( self.create_user_from_ldap_results(x[1]) )
        return users
    
    def values(self):
        app = grok.getSite()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_user_search_base,
                             scope='one',
                             filter="(&(objectclass=inetOrgPerson))" )
        
        users = []
        for x in results:
            users.append( self.create_user_from_ldap_results(x[1]) )
        
        return users
    
    def __getitem__(self, key):
        "Mapping of keys (uid) to LDAP-backed User objects"
        app = grok.getSite()
        dbc = app.ldap_connection()
        results = dbc.search( app.ldap_user_search_base,
                              scope='one',
                              filter="(&(objectclass=inetOrgPerson)(uid=%s))"
                              % key
                            )
        if not results:
            raise KeyError, "User id %s does not exist." % key
        else:
            return self.create_user_from_ldap_results(results[0][1])
    
    def __contains__(self, key):
        "Tell if a user exists"
        attr = getattr(self, key, None)
        if attr:
            return attr
        else:
            return self[key]   
    
    def get(self, key, default=None):
        attr = getattr(self, key, None)
        if attr:
            return attr
        else:
            return self[key]

    def __delitem__(self, key):
        "delete user"
        app = grok.getSite()
        dbc = app.ldap_connection()
        dbc.delete( u"uid=%s,%s" % (key, app.ldap_user_search_base) )

    def __setitem__(self, key, value):
        "add new user"
        if IUser.providedBy(value):
            value.save()
        else:
            raise TypeError, "Value needs to implements IUser interface"


class User(grok.Model):
    "User"
    interface.implements(IUser)
    
    def __init__(self,
                 uid,
                 **keywords
                 ):
        self.__name__ = uid
        self.uid = uid
        self.__parent__ = keywords.get('container', None)
        self.exists_in_ldap = keywords.get('exists_in_ldap', False)
        
        for name, value in keywords.items():
            setattr(self, name, value)
    
    def save(self):
        "Writes any changes made to the User object back into LDAP"
        app = grok.getSite()
        dbc = app.ldap_connection()
        # create
        if not self.exists_in_ldap:
            # Ug. Need to scrub empty attributes from add, but keep them
            # preserved in modify so that attributes can be deleted
            entry = self.ldap_entry
            for k,v in entry.items():
                if v == []:
                    del entry[k]
                if len(v) == 1 and v[0] == u'':
                    del entry[k]
            dbc.add(self.dn, entry)
            self.exists_in_ldap = True
        # edit
        else:
            dbc.modify(self.dn, self.ldap_entry)

    @property
    def title(self):
        """Content Title, not to be confused with the LDAP Attribute 'title'
        which is the Job Title"""
        return "%s (%s)" % (self.cn, self.uid)
    
    @property
    def dn(self):
        app = grok.getSite()
        return u"uid=%s,%s" % (self.uid, app.ldap_user_search_base)
    
    @property
    def objectClasses(self):
        l = ['top', 'person', 'organizationalPerson', 'inetOrgPerson']
        for ext in component.getUtilitiesFor(IUserSchemaExtension):
            l.append(ext[1].objectClass)
        return l
    
    @property
    def ldap_entry(self):
        "Representation of the object as an LDAP entry"
        entry = { 'objectClass': self.objectClasses, }
        
        for field in core_user_fields():
            key = getattr(field.field, 'ldap_name', field.__name__)
            # the userPassword field is a special case
            if key != 'userPassword':
                value = getattr(self, field.__name__, field.field.default)
                # MOD_DELETE is represented by an empty list
                # in the ldapadapter modify() method
                if value == None: value = []
                # distinguish between SINGLE-VALUE and MULTI-VALUE fields
                if type(value) == type([]):
                    entry[key] = value
                else:
                    entry[key] = [value]
        
        for field in additional_user_fields():
            entry[field.field.ldap_name] = [unicode(
                getattr(self, field.__name__)
            )]
            
        # dn is not represented in the entry
        del entry['dn']
        
        return entry
        
    @property
    def organization(self):
        "Look-up the Organization object based on the organization attribute"
        results = Query().searchResults(
            query.Eq( ('gum_catalog', 'organization_id'), self.o )
            )
        if results:
            return list(results)[0]
    
    # officeLocation is a property that sets the user's Street
    # and Room Number. It is multi-valued, so a user.officeLocation of:
    # 
    #   ['50 West St. - 100','60 North Ave. - 202',]
    # 
    # Would set user.street and user.roomNumber to:
    # 
    #   ['50 West St.', '60 North Ave.',]
    #   ['100','202',]
    #
    def _get_officeLocation(self):
        if self.street and self.roomNumber:
            return ['%s - %s' % (x[0], x[1])
                    for x in zip(self.street, self.roomNumber)]
        elif self.street:
            return self.street
        else:
            return []
    def _set_officeLocation(self, locations):
        streets = []
        roomNumbers = []
        for location in locations:
            if location.find(' - ') != -1:
                street, roomNumber = location.split(' - ', 1)
            else:
                street = location
                roomNumber = u'Not Applicable'
            streets.append(street)
            roomNumbers.append(roomNumber)
        self.street = streets
        self.roomNumber = roomNumbers
    officeLocation = property(_get_officeLocation, _set_officeLocation)
    
    @property
    def officeLocationClean(self):
        """
        LDAP does not allow storing empty strings, and we match lists
        of Street and Room Numbers together, so if the Room Number doesn't
        apply, we store "Not Applicable". We don't need to show this in the
        UI though.
        """
        return [ location.rstrip(u' - Not Applicable')
                 for location in self.officeLocation ]
    
    def groups(self):
        "List of Groups that the User belongs to"
        app = grok.getSite()
        return app['groups'].searchGroupsByUser(self.uid)

    def changePassword(self, password, confirm):
        if password != confirm:
            return "Waaaaa!"
        encrypted_pw = '{SSHA}' + SSHA.encrypt(password).strip()
        app = grok.getSite()
        dbc = app.ldap_connection()
        dbc.modify(
            "uid=%s,%s" % (self.uid, app.ldap_user_search_base),
            {'userPassword':[encrypted_pw]}
        )
    
    def transcripts(self):
        "Transcript objects recording modifications made to this User"
        transcripts = Query().searchResults(
            query.Eq( ('gum_catalog', 'dn'), self.dn )
            )
        return sorted(transcripts)

    @property
    def extended_fields(self):
        return additional_user_fields()

class UsersIndex(grok.View):
    grok.context(Users)
    grok.name('index')
    grok.require(u'gum.View')

class UserIndex(grok.View):
    grok.context(User)
    grok.name('index')
    grok.require(u'gum.View')

    @property
    def transcripts_by_dn(self):
        url = self.url(grok.getSite()['transcripts'],'by-dn')
        url += '?'
        url += urlencode( [ ('dn', self.context.dn) ] )
        return url
    
    def recent_transcripts(self):
        transcripts = self.context.transcripts()
        # Catalog ResultSet is lazy, and does not support slicing
        transcripts = [x for x in transcripts]
        return transcripts[:5]


class EditUser(grok.EditForm):
    grok.context(User)
    grok.name('edituser')
    grok.require(u'gum.Edit')
    
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    @property
    def form_fields(self):
        # this is a property because class attributes are computed
        # before components which provide schema extensions are registered
        form_fields = grok.AutoFields(User)
        form_fields = form_fields.select(
                        'uid',
                        'userPassword',
                        'cn',
                        'sn',
                        'givenName',
                        'email',
                        'telephoneNumber',
                        'description',
                        'job_title',
                        'employeeType',
                        'officeLocation',
                        'o',
                        'ou',)
        # uid should not be edited after an account has been created!
        # (although sometimes a typo is made in account creation, so perhaps
        #  a special form or UI to handle this use-case maybe? say if the 
        #  account is less than 5 minutes old ...)
        form_fields['uid'].for_display = True
        
        extra_fields = FormFields(*additional_user_fields())
        # XXX we lie about IUserSchemaExtensions being IUser objects to
        # get around FormFields behaviour of adapter = interface(context)
        # a better fix might be refacter the IUser interfaces in some
        # manner ...
        for f in extra_fields: f.interface = IUser
        form_fields += extra_fields
        return form_fields
    
    label = "Edit User"
    
    @grok.action('Save Changes')
    def edit(self, **data):
        # handle password changes seperately
        if data['userPassword']:
            self.context.changePassword(
                data['userPassword'], data['userPassword']
            )
        
        # TO-DO oh the hackery!!!
        self.context.principal_id = self.request.principal.id
        self.applyData(self.context, **data)
        self.context.save()
        self.redirect(self.url(self.context))


class DeleteUser(grok.View):
    grok.context(Users)
    grok.name('deleteuser')
    grok.require(u'gum.Edit')
    
    def render(self):
        id = self.request.form.get('id')
        user = self.context[ id ]
        # TO-DO oh the hackery!!!
        user.principal_id = self.request.principal.id
        event.notify( grok.ObjectModifiedEvent(user) )
        del self.context[ id ]
        self.redirect(self.url(self.context))

class GrantMembership(grok.View):
    grok.context(User)
    grok.name('grant')
    grok.require(u'gum.Edit')
    
    def update(self):
        gid = self.request.form.get('gid', None)
        group = grok.getSite()['groups'][gid]
        if self.context.uid not in group.uids:
            group.uids = group.uids + (self.context.uid,)
            
            # TO-DO oh the hackery!!!
            group.principal_id = self.request.principal.id
            event.notify( grok.ObjectModifiedEvent(group) )
            
            # save must be called after event notification, otherwise it
            # can't diff between the before and after states!
            group.save()


class RevokeMembership(grok.View):
    grok.context(User)
    grok.name('revoke')
    grok.require(u'gum.Edit')
    
    def update(self):
        gid = self.request.form.get('gid', None)
        if not gid: return
        group = grok.getSite()['groups'][gid]
        new_group = []
        for uid in group.uids:
            if uid != self.context.uid:
                new_group.append(uid)
        group.uids = new_group
        
        # TO-DO oh the hackery!!!
        group.principal_id = self.request.principal.id
        event.notify( grok.ObjectModifiedEvent(group) )
        
        # save must be called after event notification, otherwise it
        # can't diff between the before and after states!
        group.save()
    
    def render(self):
        # TO-DO: pass a status message to the UI
        self.redirect(self.url(self.context))


class GroupMemberlistSlot(grok.ViewletManager):
    "Provide application logo and tabs for the top of the page"
    grok.name('groups.memberlist')
    grok.context(User)

class GroupMemberlist(grok.Viewlet):
    grok.context(User)
    grok.viewletmanager(GroupMemberlistSlot)


class AutoCompleteSearchGidAddable(grok.View):
    grok.context(User)
    grok.name('autocompletesearchgidaddable')
    grok.require(u'gum.View')

    def groups(self):
        search_term = ldap.filter.escape_filter_chars(
            self.request.form.get('search_term', None)
        )
        if not search_term or len(search_term) < 3:
            return {}

        groups = grok.getSite()['groups']
        results = []
        
        for group in groups.search('cn', search_term, False):
            results.append(group)

        return results[:15]

    def add_url(self):
        return self.url(self.context, 'grant')
