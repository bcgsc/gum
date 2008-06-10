from zope.interface import Interface, Attribute, alsoProvides
from zope.schema import TextLine, SourceText, Password, List, Datetime, Object, Choice, Object, Int
from zope.app.content.interfaces import IContentType


class ILDAPUserGroupLocation(Interface):
    """
    LDAP location for a set of Users and Groups.
    """

    ldap_host = TextLine(
        title=u'LDAP Host',
        )
    ldap_port = TextLine(
        title=u'LDAP Port',
        )
    ldap_login = TextLine(
        title=u'LDAP Login',
        )
    ldap_password = Password(
        title=u'LDAP Password',
        )
    ldap_user_search_base = TextLine(
        title=u'LDAP User Search Base',
        )
    ldap_group_search_base = TextLine(
        title=u'LDAP Group Search Base',
    )
    ldap_admin_group = TextLine(
        title=u'Group that is granted the GUM Admin role.',
    )

class ILDAPEntry(Interface):
    """Represents any Entry within LDAP"""
    
    dn = TextLine(
        title=u"Distinguished Name (dn)",
        )

class IBaseContent(Interface):
    "Base information about a content object"
    title = TextLine(title=u"Title")


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
    cn = TextLine( title=u"Common Name",
                   description=u"Person's full name.",
                   required=True, )
    sn = TextLine( title=u"Last Name",
                   description=u"Surname, also referred to as last name or family name.",
                   required=True, )
    givenName = TextLine( title=u"First Name",
                    description=u"Person's given name.")
    uid =  TextLine( title=u"User Id",
                     description=u"Identifies the entry's userid (usually the logon ID)." )
    userpassword = Password(title=u"Password", required=False)
    email = TextLine( title=u"Email Address" )
    telephoneNumber = TextLine( title=u"Primary phone number",
                                required=False )
    street = TextLine( title=u"Street", required=False )
    roomNumber = TextLine( title=u"Room Number", required=False )
    description = SourceText(title=u"Description", required=False)
    job_title = TextLine( title=u"Job Title", required=False)
    o = TextLine( title=u"Organization", required=False,
                                 description=u"e.g. Canada's Michael Smith Genome Sciences Centre")
    ou = TextLine( title=u"Organizational Unit Name", required=False,
                                    description=u"e.g. Bioinformatics, Admin, Systems")
    employeeType = TextLine( title=u"Employee Type", required=False,
                             description=u"e.g. Full Time, Inactive, Temp")


class IGroupOfUniqueNames(ILDAPEntry):
    title = TextLine(title=u"Title", readonly=True)
    cn = TextLine(title=u"Common Name")
    description = SourceText(title=u"Description", required=False)
    uids = List(
        title=u"Member Ids",
        unique=True,
        value_type=TextLine(title=u"Member Id"),
        default=[],
    )


class IUser(IINetOrgPerson, IBaseContent):
    """
    User entry
    """
    title = TextLine(title=u"Title", readonly=True)
    
    employeeType = Choice(
                        title=u"Employee Type",
                        vocabulary="Employee Types",
                        required=False,
                        missing_value=u"Unknown"
                       )
    
    o = Choice( title=u"Organization",
                description=u"e.g. Canada's Michael Smith Genome Sciences Centre",
                vocabulary="Organizations")
    
    officeLocation = Choice(
                            title=U"Office Location",
                            vocabulary="Office Locations",
                            required=False,
                            missing_value=u"Unknown"
                            )
    ou = Choice( title=u"Organizational Unit",
                 description=u"e.g. Systems, Administration, Purchasing",
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
    dn = TextLine( title=u"Distinguished Name (dn)")
    before = List(
                  title=u"attributes before modifcation",
                  unique=True,
                  value_type=TextLine(title=u"attribute=value"),
                  )
    after = List(
                title=u"attributes after modifcation",
                unique=True,
                value_type=TextLine(title=u"attribute=value"),
                )
    observation_datetime = Datetime(title=u"Observation DateTime")
    principal_id = TextLine(title=u"Principal Id")
    
    user = Attribute("User object who made the modification")


class IOfficeLocation(Interface):
    "A Physical Location to which snail mail can be sent"
    title = TextLine(
        title=u"Office Title",
        description=u"Short, descriptive name, e.g. Echelon or BCCRC")
    street = TextLine(title=u"Street", required=False)
    postalAddressSuite = TextLine(
        title=u"Postal Address Suite",
        description=u"Location where mail should be delivered to within a building's street address. E.g. Suite 100",
        required=False )
    localityName = TextLine(title=u"City", required=False)
    st = TextLine(title=u"Provine or State", required=False)
    postalCode = TextLine(title=u"Postal Code", required=False)
    telephoneNumber = TextLine(title=u"Telephone Number", required=False)
    fax = TextLine(title=u"Fax", required=False)
    rooms = List(
                 title=u"Rooms",
                 unique=True,
                 value_type=TextLine(title=u"Room"),
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
    id = TextLine(title=u"Id")
    description = SourceText(title=u"Description", required=False)
    employeeTypes = List(
                      title=u"Employee Types",
                      unique=True,
                      required=False,
                      default=[],
                      value_type=TextLine(title=u"Employee Type")
                     )
    orgunitTypes = List(
                    title=u"Organizational Unit Types",
                    unique=True,
                    required=False,
                    default=[],
                    value_type=TextLine(title=u"Organizational Unit Type")
                    )
    member_count = Int(title=u"Member Count", readonly=True)
    offices = List( title=u"Office Locations",
                    unique=True,
                    readonly=True,
                    default=[],
                    value_type=Object( title=u"Office Location",
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
    organizations = List(
            title=u"Organizations",
            unique=True,
            required=False,
            value_type=TextLine(title=u"Organization"),
        )
    employeeTypes = List(
            title=u"Employee Types",
            unique=True,
            required=False,
            value_type=TextLine(title=u"Employee Type"),
        )
    streets = List(
            title=u"Streets",
            unique=True,
            required=False,
            value_type=TextLine(title=u"Street"),
        )
    orgunitTypes = List(
            title=u"Organizational Unit Types",
            unique=True,
            required=False,
            value_type=TextLine(title=u"Organizational Unit Type"),
    )


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
