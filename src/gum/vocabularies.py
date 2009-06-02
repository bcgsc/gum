from zope.interface import alsoProvides, Interface 
from zope.schema.interfaces import IVocabularyFactory 
from zope.schema.vocabulary import SimpleVocabulary 
import grok 

class OrganizationsVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        app = grok.getApplication()
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
            return SimpleVocabulary.fromValues(context.officeLocation)
        officeRooms = {}
        for office in offices:
            if office.rooms:
                for room in office.rooms:
                    loc = '%s - %s' % (office.street, room)
                    officeRooms[loc] = loc
            else:
                officeRooms[office.street] = office.street
        
        # account for locations which are not part of vocab
        # (which are allowed to stay the same)
        for current_location in context.officeLocation:
            if current_location.find(' - Not Applicable') != -1:
                hr_loc = current_location[:current_location.find(' - Not Applicable')]
            else:
                hr_loc = current_location
            officeRooms[hr_loc] = current_location
        
        return SimpleVocabulary.fromItems(officeRooms.items())

grok.global_utility(factory=OfficeLocationsVocab, name="Office Locations")


class OrganizationalUnitsVocab(object):
    grok.implements(IVocabularyFactory)
    
    def __call__(self, context):
        try:
            ouTypes = context.organization.orgunitTypes
        except AttributeError:
            ouTypes = []
            
        # account for values not part of the vocab
        try:
            if context.ou not in ouTypes:
                ouTypes.append(context.ou)
        except AttributeError:
            pass
        
        return SimpleVocabulary.fromValues(ouTypes)

grok.global_utility(factory=OrganizationalUnitsVocab, name='Organizational Units')
