from urllib import urlencode

from zope import schema, interface
from zope import event
from zope.lifecycleevent import ObjectCreatedEvent, ObjectModifiedEvent

import grok
from gum.interfaces import ISmartSearches, ISmartSearch


class SmartSearches(grok.Container):
    "Contains Smart Searches"
    interface.implements(ISmartSearches)


class SmartSearch(grok.Model):
    "Smart Search"
    interface.implements(ISmartSearch)
    
    def __init__(self,
                 id,
                 title='',
                 organizations=[],
                 employeeTypes=[],
                 streets=[],
                 orgunitTypes=[],
                ):
        self.__name__ = id
        self.title = title
        self.organizations = organizations
        self.employeeTypes = employeeTypes
        self.streets = streets
        self.orgunitTypes = orgunitTypes


class SmartSearchesIndex(grok.View):
    grok.context(SmartSearches)
    grok.name('index')
    grok.require(u'gum.View')

    def smartsearches(self):
        return self.context.values()


class AddSmartSearch(grok.AddForm):
    grok.context(SmartSearches)
    grok.name('addsmart')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.Fields(
        id=schema.TextLine(title=u"id"))
    form_fields += grok.AutoFields(SmartSearch)
    label = "Add Smart Search"
    
    @grok.action('Add Smart Search')
    def add(self, id, **data):
        smrt = SmartSearch(id, **data)
        smrt.principal_id = self.request.principal.id # XXX oh the hackery!!!
        self.context[id] = smrt
        event.notify( ObjectCreatedEvent(smrt) )
        self.redirect(self.url(self.context[id]))


class EditSmartSearch(grok.EditForm):
    grok.context(SmartSearch)
    grok.name('editsmart')
    grok.require(u'gum.Edit')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.AutoFields(SmartSearch)

    label = "Edit Smart Search"
    
    @grok.action('Save Changes')
    def edit(self, **data):
        # TO-DO oh the hackery!!!
        self.context.principal_id = self.request.principal.id
        self.applyData(self.context, **data) # sends grok.ObjectModifiedEvent
        self.redirect(self.url(self.context))


class DeleteSmartSearch(grok.View):
    grok.context(SmartSearch)
    grok.name('deletesmart')
    grok.require(u'gum.Edit')

    def render(self):
        id = self.request.form.get('id')
        smrt = self.context[ id ]
        # TO-DO oh the hackery!!!
        smrt.principal_id = self.request.principal.id
        event.notify( ObjectModifiedEvent(smrt) )
        del self.context[ id ]
        self.redirect(self.url(self.context))


class SmartSearchIndex(grok.View):
    grok.context(SmartSearch)
    grok.name('index')
    grok.require(u'gum.View')
    
    def users(self):
        app = grok.getApplication()
        return app['users'].orgsearch(self.context)

    def export_url_csv(self):
        url = self.url(self.context, 'orgsearch-csv')
        url += self._queryString()
        return url

    def export_url_pdf(self):
        url = self.url(self.context, 'orgsearch-pdf')
        url += self._queryString()
        return url
    
    def _queryString(self):
        qs = '?'
        params = []
        params.append( ('title', self.context.title) )
        for org in self.context.organizations:
            params.append( ('organizations:list', org) )
        for street in self.context.streets:
            params.append( ('streets:list', street) )
        for emp in self.context.employeeTypes:
            params.append( ('employeeTypes:list', emp) )
        for ou in self.context.orgunitTypes:
            params.append( ('orgunitTypes:list', ou) )
        qs += urlencode( params )
        return qs
