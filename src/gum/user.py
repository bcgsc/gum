import grok
from urllib import urlencode
from zope import schema, interface
from zope import event
from zope.lifecycleevent import ObjectModifiedEvent
from hurry.query.query import Query
from hurry import query
from ldap.modlist import addModlist, modifyModlist
import SSHA
from gum.interfaces import IUser, IUsers
from gum import getProperty, getPropertyAsSingleValue
from gum import quote


class Users(grok.Container):
    "Collection of Users"
    interface.implements(IUsers)
    
    def create_user_from_ldap_results(self, data):
        return User(
            uid=getPropertyAsSingleValue(data, 'uid', None),
            container=self,
            cn = getPropertyAsSingleValue( data, 'cn', u''),
            sn = getPropertyAsSingleValue( data, 'sn', u''),
            givenName = getPropertyAsSingleValue( data, 'givenName', u''),
            email = getPropertyAsSingleValue( data, 'mail', u''),
            telephoneNumber = getProperty( data, 'telephoneNumber', []),
            description = getPropertyAsSingleValue( data, 'description', u''),
            roomNumber = getProperty( data, 'roomNumber', []),
            street = getProperty( data, 'street', []),
            # We call it job_title, ldap calls it just title
            job_title = getPropertyAsSingleValue(data, 'title', u''),
            o = getPropertyAsSingleValue(data, 'o', u''),
            ou = getPropertyAsSingleValue(data, 'ou', u''),
            employeeType = getPropertyAsSingleValue(data, 'employeeType', u''),
            exists_in_ldap=True,
        )
    
    def search(self, param, term, exact_match=True):
        "Search through users and return matches as User objects in a list"
        app = grok.getSite()
        dbc = app.ldap_connection()
        param = quote(param)
        term = quote(term)
        
        if not exact_match:
            term = '*' + term + '*'
        
        results = dbc.search( app.ldap_user_search_base,
                              scope='one',
                              filter="(&(objectclass=inetOrgPerson)(%s=%s))"
                              % (param, term)
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
                 container=None,
                 cn=u'',
                 sn=u'',
                 givenName=u'',
                 userPassword=u'********',
                 email=u'',
                 telephoneNumber=[],
                 description=u'',
                 street=u'',
                 roomNumber=u'',
                 job_title=u'',
                 o=u'',
                 ou=u'',
                 employeeType=u'',
                 exists_in_ldap=False, ):
        self.__name__ = uid
        self.__parent__ = container
        self.uid = uid
        self.userPassword = userPassword
        self.cn = cn
        self.sn = sn
        self.givenName = givenName
        self.email = email
        self.telephoneNumber = telephoneNumber
        self.roomNumber = roomNumber
        self.street = street
        self.description = description
        self.job_title = job_title
        self.o = o
        self.ou = ou
        self.employeeType = employeeType
        self.officeLocation = []
        self.exists_in_ldap = exists_in_ldap

    def save(self):
        "Writes any changes made to the User object back into LDAP"
        app = grok.getSite()
        dbc = app.ldap_connection()
        # create
        if not self.exists_in_ldap:
            dbc.add(self.dn, self.ldap_entry)
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
    def ldap_entry(self):
        "Representation of the object as an LDAP entry"
        # XXX Waaaa?
        if not self.ou: self.ou = u''
        if not self.job_title: self.job_title = u''
        if not self.description: self.description = u''
        
        entry = { 'objectClass':
                  ['top', 'person', 'organizationalPerson', 'inetOrgPerson'],}
        # TO-DO clean-up
        for attrname in ['cn','sn','givenName','description','o','ou',
                         'employeeType','uid',]:
            if getattr(self, attrname, None):
                entry[attrname] = [getattr(self, attrname, None),]

        if getattr(self, 'telephoneNumber'):
            entry['telephoneNumber'] = getattr(self, 'telephoneNumber')
        if getattr(self, 'roomNumber'):
            entry['roomNumber'] = getattr(self, 'roomNumber')
        if getattr(self, 'street'):
            entry['street'] = getattr(self, 'street')
        if getattr(self, 'job_title', None):
            entry['title'] = [getattr(self, 'job_title', None),]
        if getattr(self, 'email', None):
            entry['mail'] = [getattr(self, 'email', None),]
        
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
        org = self.o
        if not org:
            return []
        if self.street and self.roomNumber:
            return ['%s - %s' % (x[0], x[1])
                    for x in zip(self.street, self.roomNumber)]
        else:
            return self.street
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
        return transcripts


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
        return transcripts[:3]


class EditUser(grok.EditForm):
    grok.context(User)
    grok.name('edituser')
    grok.require(u'gum.Edit')
    
    template = grok.PageTemplateFile('gum_edit_form.pt')
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
    
    label = "Edit User"
    
    @grok.action('Save Changes')
    def edit(self, **data):
        # handle password changes seperately
        if data['userPassword'] != u'********':
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
        event.notify( ObjectModifiedEvent(user) )
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
            group.uids.append(self.context.uid)
            group.save()
            # TO-DO oh the hackery!!!
            group.principal_id = self.request.principal.id
            event.notify( ObjectModifiedEvent(group) )


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
        group.save()
        # TO-DO oh the hackery!!!
        group.principal_id = self.request.principal.id
        event.notify( ObjectModifiedEvent(group) )
    
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
        search_term = self.request.form.get('search_term', None)
        if not search_term or len(search_term) < 3:
            return {}

        groups = grok.getSite()['groups']
        results = []
        
        for group in groups.search('cn', search_term, False):
            results.append(group)

        return results[:15]

    def add_url(self):
        return self.url(self.context, 'grant')
