import grok
from StringIO import StringIO
from urllib import urlencode
from zope import interface
from zope.app.container.interfaces import INameChooser

from gum.interfaces import IOrganizations, IOrganization, IOfficeLocation
from gum.smart import SmartSearch

class Organizations(grok.Container):
    interface.implements(IOrganizations)


class Organization(grok.Container):
    interface.implements(IOrganization)
    
    def __init__(self, id, title=u'', description=u'', employeeTypes=[], orgunitTypes=[]):
        super(Organization, self).__init__()
        self.id = id
        self.title = title
        self.description = description
        self.employeeTypes = employeeTypes
        self.orgunitTypes = orgunitTypes
    
    @property
    def offices(self):
        return self.values()

    @property
    def member_count(self):
        app = grok.getSite()
        return app['users'].search_count('o', self.id)

    @property
    def users(self):
        app = grok.getSite()
        return app['users'].search('o', self.title)


class OfficeLocation(grok.Model):
    interface.implements(IOfficeLocation)

    def __init__( self, title=u'', street=u'', postalAddressSuite=u'',
                  localityName=u'', st=u'', postalCode=u'',
                  telephoneNumber=u'', fax=u'', rooms=[]  
                ):
        self.title = title
        self.street = street
        self.postalAddressSuite = postalAddressSuite
        self.localityName = localityName
        self.st = st
        self.postalCode = postalCode
        self.telephoneNumber = telephoneNumber
        self.fax = fax
        self.rooms = rooms


# Views for collections of organizations
class OrganizationsIndex(grok.View):
    grok.context(Organizations)
    grok.name('index')
    grok.require(u'gum.View')


class AddOrganization(grok.AddForm):
    grok.context(Organizations)
    grok.name('addorg')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.AutoFields(Organization)
    form_fields = form_fields.select( 'title',
                                      'id',
                                      'description',
                                      'employeeTypes',
                                      'orgunitTypes',
                                    )
    
    label = "Add Organization"

    @grok.action('Add Organization')
    def add(self, **data):
        orgid = data['id']
        org = Organization(**data)
        self.context[orgid] = org
        self.redirect(self.url(self.context[orgid]))


class OrgSearch(grok.View):
    grok.context(Organizations)
    grok.name('orgsearch')
    grok.require(u'gum.View')

    def update(self):
        self.usersearch = SmartSearch(
            'temp',
            organizations = self.request.form.get('organizations',[]),
            streets = self.request.form.get('streets',[]),
            employeeTypes = self.request.form.get('employeeTypes',[]),
            orgunitTypes = self.request.form.get('orgunitTypes',[]),
        )

    def results(self):
        app = grok.getSite()
        return app['users'].orgsearch(self.usersearch)

    def export_url(self):
        url = self.url(self.context, 'orgsearch-csv')
        url += '?'
        params = []
        for org in self.usersearch.organizations:
            params.append( ('organizations:list', org) )
        for street in self.usersearch.streets:
            params.append( ('streets:list', street) )
        for emp in self.usersearch.employeeTypes:
            params.append( ('employeeTypes:list', emp) )
        for ou in self.usersearch.orgunitTypes:
            params.append( ('orgunitTypes:list', ou) )
        url += urlencode( params )
        return url


class OrgSearchCSV(grok.View):
    grok.context(interface.Interface) # applies to all objects
    grok.name('orgsearch-csv')
    grok.require(u'gum.View')

    def update(self):
        self.usersearch = SmartSearch(
            'temp',
            organizations=self.request.form.get('organizations',[]),
            streets=self.request.form.get('streets',[]),
            orgunitTypes=self.request.form.get('orgunitTypes',[]),
            employeeTypes=self.request.form.get('employeeTypes',[]),
        )

    def render(self):
        app = grok.getSite()
        out = StringIO()
        out.write('"Name","Email","Phone","User Id","Office Location","Employee Type","Organizational Unit Type"\n')
        for user in app['users'].orgsearch(self.usersearch):
            if user.roomNumber:
                location = '%s - %s' % (user.street, user.roomNumber)
            else:
                location = user.street
            if user.telephoneNumber:
                phone = ', '.join(user.telephoneNumber)
            else:
                phone = ''
            out.write( '"%s","%s","%s","%s","%s","%s","%s"\n' % (
                       user.cn, user.email, phone, user.uid, location, user.employeeType, user.ou
                     ) )
        return out.getvalue()


class OrgSearchPDF(grok.View):
    grok.context(interface.Interface) # applies to all objects
    grok.name('orgsearch-pdf')
    grok.require(u'gum.View')

    def update(self):
        self.usersearch = SmartSearch(
            'temp',
            title=self.request.form.get('title','GUM Export'),
            organizations=self.request.form.get('organizations',[]),
            streets=self.request.form.get('streets',[]),
            orgunitTypes=self.request.form.get('orgunitTypes',[]),
            employeeTypes=self.request.form.get('employeeTypes',[]),
        )
        self.filename = self.request.form.get('fname','gum-export.pdf')
 
    def render(self):
        from tempfile import TemporaryFile
        from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Table
        from reportlab.lib import styles, units, pagesizes, colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import inch
        
        # Style for the PDF
        stylesheet = styles.getSampleStyleSheet()
        stylesheet.add(ParagraphStyle(name='Head',
                                      fontName='Helvetica',
                                      fontSize=8,
                                      leading=12,
                                      textColor=colors.white, )
                       )
        stylesheet['title'].fontName = 'Helvetica'
        stylesheet['Normal'].fontName = 'Helvetica'
        stylesheet['Normal'].fontSize=8
        
        # get the data for the table
        app = grok.getSite()
        data = {}

        for user in app['users'].orgsearch(self.usersearch):
            if user.roomNumber:
                location = '%s - %s' % (user.street, user.roomNumber)
            else:
                location = user.street
            data[user.cn] = {'email':user.email,
                             'phone':user.telephoneNumber,
                             'job_title':user.job_title,
                             'location':location}
        names = data.keys()
        names.sort()
        
        # Style the Table
        styleinfo = [ 
            ('BACKGROUND', (0,0), (-1,0),   colors.black),
            ('TEXTCOLOR',  (0,0), (-1,0),   colors.white),
            ('GRID',       (0,0), (-1,-1),  1, colors.black),
            ('ALIGN',      (0,0), (-1,-1),  'LEFT'),
            ('VALIGN',     (0,0), (-1,-1),  'TOP'),
        ]
        for i in range(2, len(data), 2):
            styleinfo.append( ('BACKGROUND', (0,i), (-1,i), colors.whitesmoke) )
        
        tblstyle = TableStyle( styleinfo )
        
        # flow the data into PDF structures
        pdf = []
        pdf.append( [
            Paragraph("Name", stylesheet['Head']),
            Paragraph("Email", stylesheet['Head']),
            Paragraph("Phone", stylesheet['Head']),
            Paragraph("Job Title", stylesheet['Head']),
            Paragraph("Office Location", stylesheet['Head']), 
        ] )
        for name in names:
            pdf.append(  [
                Paragraph( name, stylesheet['Normal'] ),
                Paragraph( data[name]['email'], stylesheet['Normal'] ),
                Paragraph( data[name]['phone'], stylesheet['Normal'] ),
                Paragraph( data[name]['job_title'], stylesheet['Normal'] ),
                Paragraph( data[name]['location'], stylesheet['Normal'] ),
            ] )
        
        # Generate and return the PDF
        response = self.request.response
        response.setHeader('Content-Disposition',
                           'attachment; filename=%s' % self.filename)
        response.setHeader('Content-Type', 'application/pdf')
        

        table = Table(pdf)
        table.setStyle(tblstyle)
        
        doc_structure = [
            Paragraph(self.usersearch.title, stylesheet['title']),
            table
            ]
        
        tempfile = TemporaryFile()
        padding = 0.5 * inch
        doc = SimpleDocTemplate( tempfile,
                                 pagesize=pagesizes.A4,
                                 leftMargin=padding,
                                 rightMargin=padding,
                                 topMargin=padding,
                                 bottomMargin=padding, )
        doc.build(doc_structure)
        return tempfile


# Views for a single organization
class OrganizationIndex(grok.View):
    "Display an Organization"
    grok.context(Organization)
    grok.name('index')
    grok.require(u'gum.View')

    def is_admin(self):
        # TO-DO: supporting Organization editing, could be removed in a
        # future UI clean-up
        from zope.securitypolicy.interfaces import IGrantInfo
        grant_info = IGrantInfo( grok.getSite() )
        for role in grant_info.getRolesForPrincipal(self.request.principal.id):
            if role[0] == u'gum.Admin':
                return True
        return False

class OrganizationEdit(grok.EditForm):
    "Form to edit an Organization"
    grok.context(Organization)
    grok.name('editorg')
    grok.require(u'gum.Edit')
    template = grok.PageTemplateFile('gum_edit_form.pt')

    label = 'Edit Organization'
    form_fields = grok.AutoFields(Organization)
    form_fields = form_fields.select('title','description','orgunitTypes','employeeTypes')
    
    @grok.action('Save changes')
    def edit(self, **data):
        self.applyData(self.context, **data)
        self.redirect(self.url(self.context))


class DeleteOrganization(grok.View):
    grok.context(Organizations)
    grok.name('deleteorg')
    grok.require(u'gum.Edit')

    def update(self):
        # XXX referential integrity - first query the Users
        # although we may allow arbitrary setting of o/ou fields
        # or editing of those fields by another client, so ref int
        # might not be a given
        orgid = self.request.form.get('id', None)
        if orgid:
            del self.context[orgid]

    def render(self):
        self.redirect(self.url(self.context))


# Views for an Office Location
class OfficeLocationAdd(grok.AddForm):
    grok.context(Organization)
    grok.name('addofficelocation')
    grok.require(u'gum.Add')
    template = grok.PageTemplateFile('gum_edit_form.pt')
    
    form_fields = grok.AutoFields(OfficeLocation)
    label = "Add Office Location"

    @grok.action('Add Office Location')
    def add(self, **data):
        officelocation = OfficeLocation(**data)
        name = INameChooser(self.context).chooseName(u'', officelocation)
        self.context[name] = officelocation
        self.redirect(self.url(self.context))


class OfficeLocationEdit(grok.EditForm):
    "Form to edit an Organization"
    grok.context(OfficeLocation)
    grok.name('editofficelocation')
    grok.require(u'gum.Edit')
    template = grok.PageTemplateFile('gum_edit_form.pt')

    label = 'Edit Office Location'
    form_fields = grok.AutoFields(OfficeLocation)

    @grok.action('Save changes')
    def edit(self, **data):
        self.applyData(self.context, **data)
        self.redirect(self.url(self.context.__parent__))


class DeleteOfficeLocation(grok.View):
    grok.context(Organization)
    grok.name('deleteofficelocation')
    grok.require(u'gum.Edit')

    def update(self):
        officeid = self.request.form.get('id', None)
        if officeid:
            del self.context[officeid]

    def render(self):
        self.redirect(self.url(self.context))

