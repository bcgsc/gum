import grok
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import alsoProvides, Interface

class OrganizationsVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        app = grok.getSite()
        orgs = [org.id for org in app['orgs'].values()]
        orgs.append('Unknown')
        return SimpleVocabulary.fromValues(orgs)

grok.global_utility(factory=OrganizationsVocab, name="Organizations")            


class EmployeeTypeVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        try:
            employeeTypes = context.organization.employeeTypes
        except AttributeError:
            employeeTypes = []
        return SimpleVocabulary.fromValues(
            employeeTypes
        )

grok.global_utility(factory=EmployeeTypeVocab, name="Employee Types")


class OfficeLocationsVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        try:
            offices = context.organization.offices
        except AttributeError:
            offices = None
        if not offices:
            return SimpleVocabulary.fromValues([])
        else:
            officeRooms = []
            for office in offices:
                if office.rooms:
                    for room in office.rooms:
                        officeRooms.append('%s - %s' % (office.street, room))
                else:
                    officeRooms.append(office.street)
            
            return SimpleVocabulary.fromValues(officeRooms)

grok.global_utility(factory=OfficeLocationsVocab, name="Office Locations")


class OrganizationalUnitsVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        try:
            ouTypes = context.organization.orgunitTypes
        except AttributeError:
            ouTypes = []
        return SimpleVocabulary.fromValues(ouTypes)

grok.global_utility(factory=OrganizationalUnitsVocab, name='Organizational Units')
