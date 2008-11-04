from zope.interface import Interface, Attribute, alsoProvides
from zope import schema
from zope.app.content.interfaces import IContentType


class ILDAPUserGroupLocation(Interface):
    """
    LDAP location for a set of Users and Groups.
    """

    ldap_host = schema.TextLine(
        title=u'LDAP Host',
        )
    ldap_port = schema.TextLine(
        title=u'LDAP Port',
        )
    ldap_login = schema.TextLine(
        title=u'LDAP Login',
        )
    ldap_password = schema.Password(
        title=u'LDAP Password',
        )
    ldap_user_search_base = schema.TextLine(
        title=u'LDAP User Search Base',
        )
    ldap_group_search_base = schema.TextLine(
        title=u'LDAP Group Search Base',
    )
    ldap_admin_group = schema.TextLine(
        title=u'Group that is granted the GUM Admin role.',
    )

class ILDAPEntry(Interface):
    """Represents any Entry within LDAP"""
    
    dn = schema.TextLine(
        title=u"Distinguished Name (dn)",
        )

class IBaseContent(Interface):
    "Base information about a content object"
    title = schema.TextLine(title=u"Title")


class IINetOrgPerson(ILDAPEntry):
    """
    This schema is define din RFC 2798:
    
    http://www.faqs.org/rfcs/rfc2798.html
    
    The inetOrgPerson object class is a general purpose object class that
    holds attributes about people.The attributes it holds were chosen
    to accommodate information requirements found in typical Internet and
    Intranet directory service deployments.
    
    Note that 'title' attribute has been renamed to 'job_title' to avoid
    clashing with the title attribute provided by BaseContent :(
    """
    # only a partial implementation!
    cn = schema.TextLine( title=u"Common Name",
                   description=u"""Person's full name. This name is
semi-formal and intended to reflect what someone wishes to be called,
for example non-native English person may adopt an english name which people
refer to them as.""",
                   required=True, )
    sn = schema.TextLine( title=u"Last Name",
                   description=u"Surname, also referred to as last name or family name.",
                   required=True, )
    givenName = schema.TextLine( title=u"First Name",
                    description=u"Person's given name. This name should be official, e.g. matching the name used on a passport.")
    uid =  schema.TextLine( title=u"User Id",
                     description=u"A unique identifier, typically used as a logon id." )
    userPassword = schema.TextLine(
        title=u"Password",
        description=u"""
Passwords are stored encyrpted and so can not be displayed. Please take care
when changing the password of an account! Typically if you wish to de-activate
an account, you should remove the groups from an account that grant that 
account access. Scrambling the password does not de-activate the account,
since it may be possible for a user to reset their password through an 
e-mail authetenticated password reset service!
""",
        required=False)
    email = schema.TextLine( title=u"Email Address",
        description=u"""
This e-mail address may be used to authenticate the account to recover lost passwords.""",
    )
    telephoneNumber = schema.List(
        title=u"Phone Numbers",
        description=u"The first number listed is intended to be the primary phone number.",
        required=False,
        default=[],
        value_type=schema.TextLine( title=u"Phone number",),
    )
    street = schema.TextLine( title=u"Street", required=False )
    roomNumber = schema.TextLine( title=u"Room Number", required=False )
    description = schema.SourceText(
        title=u"Description",
        description=u"Notes about the account, such as what the account is for.",
        required=False
    )
    job_title = schema.TextLine( title=u"Job Title", required=False)
    o = schema.TextLine( title=u"Organization", required=False,)
    ou = schema.TextLine( title=u"Organizational Unit Name", required=False,
                          description=u"e.g. Bioinformatics, Admin, Systems")
    employeeType = schema.TextLine( title=u"Employee Type", required=False,
                             description=u"e.g. Full Time, Inactive, Temp")


class IGroupOfUniqueNames(ILDAPEntry):
    title = schema.TextLine(title=u"Title", readonly=True)
    cn = schema.TextLine(title=u"Common Name")
    description = schema.SourceText(title=u"Description", required=False)
    uids = schema.List(
        title=u"Member Ids",
        unique=True,
        value_type=schema.TextLine(title=u"Member Id"),
        default=[],
    )


class IUser(IINetOrgPerson, IBaseContent):
    """
    User entry
    """
    title = schema.TextLine(title=u"Title", readonly=True)
    
    employeeType = schema.Choice(
        title=u"Employee Type",
        description=u"""
Choices available is based on the Organizational field.
        """,
        vocabulary="Employee Types",
        required=False,
        missing_value=u"Unknown"
    )
    o = schema.Choice( title=u"Organization",
                       description=u"""
Identifier of an organization. After choosing this field and saving the change,
the Employee Type, Office Location and Organizational Unit field dropdown will
change based on the settings for that Organization.
""",
                       vocabulary="Organizations",
    )
    officeLocation = schema.List(
        title=u'Office Locations',
        description=u"""
        First location is the primary one. The choice of locations is based on the
        current Organization the account belongs to.""",
        value_type=schema.Choice(
            title=u"Office Location",
            vocabulary="Office Locations",
            required=True,
        ),
    )
    ou = schema.Choice(
        title=u"Organizational Unit",
        description=u"e.g. Systems, Administration, Purchasing.",
        vocabulary="Organizational Units",
        required=False
    )
    
    def changePassword(self, password, confirm):
        "Change the User Password"
    
    def load(self):
        "Fetch the User data from LDAP"
    
    def save(self):
        "Saves the User object into LDAP"
        
    def ldap_entry(self):
        "Python representation of the User object as an LDAP Entry"

    def transcripts(self):
        "List of Transcipt objects"


class IUsers(Interface):
    """
    Collection of Users
    """
    
    def orgsearch(self, search_criteria):
        """
        search_criteria must implement ISmartSearch
        """
    
    def search_count(self, param, term):
        """
        Search through users, but only return a count of matches
        """
    
    def search(self, param, term, exact_match=True):
        """
        Search through users and return matches as User objects in a list
        """


class IGroup(IGroupOfUniqueNames, IBaseContent):
    """
    Group of Unique names entry
    """

    def load(self):
        "Fetch the Group data from LDAP"

    def ldap_entry(self):
        "Python representation of the Groiup object as an LDAP Entry"

    def transcripts(self):
        "List of Transcipt objects"



class ITranscripts(Interface):
    "Contains Transcripts"


class ITranscript(Interface):
    """
    Record of a modification to an LDAP entry
    """
    dn = schema.TextLine( title=u"Distinguished Name (dn)")
    before = schema.List(
                  title=u"attributes before modifcation",
                  unique=True,
                  value_type=schema.TextLine(title=u"attribute=value"),
                  )
    after = schema.List(
                title=u"attributes after modifcation",
                unique=True,
                value_type=schema.TextLine(title=u"attribute=value"),
                )
    observation_datetime = schema.Datetime(title=u"Observation DateTime")
    principal_id = schema.TextLine(title=u"Principal Id")
    
    user = Attribute("User object who made the modification")


class IOfficeLocation(Interface):
    "A Physical Location to which snail mail can be sent"
    title = schema.TextLine(
        title=u"Office Title",
        description=u"Short, descriptive name, e.g. Echelon or BCCRC")
    street = schema.TextLine(title=u"Street", required=False)
    postalAddressSuite = schema.TextLine(
        title=u"Postal Address Suite",
        description=u"Location where mail should be delivered to within a building's street address. E.g. Suite 100",
        required=False )
    localityName = schema.TextLine(title=u"City", required=False)
    st = schema.TextLine(title=u"Provine or State", required=False)
    postalCode = schema.TextLine(title=u"Postal Code", required=False)
    telephoneNumber = schema.TextLine(title=u"Telephone Number", required=False)
    fax = schema.TextLine(title=u"Fax", required=False)
    rooms = schema.List(
                 title=u"Rooms",
                 unique=True,
                 value_type=schema.TextLine(title=u"Room"),
                 required=False,
                 default=[],
                 )


class IOrganizations(Interface):
    "Contains Organizations"


class IOrganization(IBaseContent):
    """
    Information about an Organization, primarily useful
    for providing constraints for the User UI.
    """
    id = schema.TextLine(title=u"Id")
    description = schema.SourceText(title=u"Description", required=False)
    employeeTypes = schema.List(
                      title=u"Employee Types",
                      unique=True,
                      required=False,
                      default=[],
                      value_type=schema.TextLine(title=u"Employee Type")
                     )
    orgunitTypes = schema.List(
                    title=u"Organizational Unit Types",
                    unique=True,
                    required=False,
                    default=[],
                    value_type=schema.TextLine(title=u"Organizational Unit Type")
                    )
    member_count = schema.Int(title=u"Member Count", readonly=True)
    offices = schema.List( title=u"Office Locations",
                    unique=True,
                    readonly=True,
                    default=[],
                    value_type=schema.Object( title=u"Office Location",
                                       schema=IOfficeLocation ),
                  )


class ISmartSearches(Interface):
    "Contains Smart Searches"


class ISmartSearch(Interface, IBaseContent):
    """
    Smart Search contains search criteria for a
    search specific to a set of Users.
    
    An example:
    
      All Users who's Organization is 'BCGSC', who's Employee Type is
      either Full Time, Part Time or Temp, who's Street Location is 
      Echolon or BCCRC, and who's Organizational Unit Type is 
      Bioinformatics.
    
    """
    organizations = schema.List(
            title=u"Organizations",
            unique=True,
            required=False,
            value_type=schema.TextLine(title=u"Organization"),
        )
    employeeTypes = schema.List(
            title=u"Employee Types",
            unique=True,
            required=False,
            value_type=schema.TextLine(title=u"Employee Type"),
        )
    streets = schema.List(
            title=u"Streets",
            unique=True,
            required=False,
            value_type=schema.TextLine(title=u"Street"),
        )
    orgunitTypes = schema.List(
            title=u"Organizational Unit Types",
            unique=True,
            required=False,
            value_type=schema.TextLine(title=u"Organizational Unit Type"),
    )


class IExtensionMaker(Interface):
    def new():
        "Create a new IExtension instance"
    def load():
        "Load an existing IExtension instance"

class IExtension(Interface):
    title = schema.TextLine(title=u"Title")


#
# Content Type Info is stored as Tagged Values on the content interfaces
#
IUser.setTaggedValue('typename',u'User')
IUser.setTaggedValue('actions', { 'edit'   : {'name' : 'edituser'},
                                  'delete' : {'name' : 'deleteuser'}
                                 } )
alsoProvides(IUser, IContentType)

IGroup.setTaggedValue('typename',u'Group')
IGroup.setTaggedValue('actions', { 'edit'   : {'name' : 'editgroup'},
                                   'delete' : {'name' : 'deletegroup'}
                                 } )
alsoProvides(IGroup, IContentType)

IOrganization.setTaggedValue('typename', 'Organization')
IOrganization.setTaggedValue('actions', { 'edit'   : {'name' : 'editorg'},
                                   'delete' : {'name' : 'deleteorg'}
                                 } )
alsoProvides(IOrganization, IContentType)

ISmartSearch.setTaggedValue('typename', u'Smart Search')
ISmartSearch.setTaggedValue('actions', { 'edit'   : {'name' : 'editsmart'},
                                         'delete' : {'name' : 'deletesmart'}
                                 } )
alsoProvides(ISmartSearch, IContentType)
