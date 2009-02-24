from zope import schema 
import grok 
import martian 
import re 
import zope.app.component 

# monkey pizatchel charges!
def getApplication():
    site = zope.app.component.hooks.getSite()
    if grok.interfaces.IApplication.providedBy(site):
        return site
    else:
        # another sub-site is within the application, walk up
        # the tree until we get to the application
        obj = site
        while not grok.interfaces.IApplication.providedBy(obj):
            obj = obj.__parent__
        return obj

grok.getApplication = getApplication

class View(grok.Permission):
    grok.name(u'gum.View')

class Add(grok.Permission):
    grok.name(u'gum.Add')

class Edit(grok.Permission):
    grok.name(u'gum.Edit')

class EditGroup(grok.Permission):
    grok.name(u'gum.EditGroup')

class Manager(grok.Permission):
    grok.name('zope.Manager')

def getPropertyAsSingleValue( data, name, default ):
    """
    Read a property from an LDAP data structure.
    Multi-valued properties are read as single-valued,
    with only the first value being used.
    """
    try:
        return data[name][0]
    except (IndexError, KeyError):
        return default

def getProperty( data, name, default ):
    """
    Read a property from an LDAP data structure.
    Return a default value if name-value pair does not exist.
    """
    try:
        return data[name]
    except (IndexError, KeyError):
        return default

def edit_form_template():
    """Return a Page Template suitable for usage in GUM Form Views"""
    return grok.PageTemplateFile('gum_edit_form.pt')

class CheckRequireGrokker(martian.ClassGrokker):
    """
    Require that all Views be protected, excpet the "loginpage" View.
    """
    martian.component(grok.View)
    martian.directive(grok.require, name='permission')

    def execute(self, class_, permission, **data):
        if not permission and \
        str(class_) != "<class 'gum.login.LoginPage'>":
            raise grok.GrokError(
                'This application requires %r to use the grok.require '
                'directive!' % class_, class_)
        return True

def decombobulate(field, data):
    """
    Translate values from LDAP fields to zope.schema fields.
    
    The 'ldap_as_multivalued' attribute on a zope.schema field
    specifies if a LDAP MULTI-VALUED field should be treated
    as single-valued in the context of GUM.
    
    The 'ldap_name' attribute on a zope.schema field specifies
    the name that field is mapped to in LDAP.
    """
    as_multi = getattr(field, 'ldap_as_multivalued', False)
    ldap_name = getattr(field, 'ldap_name', field.__name__)
    
    try:
        value = data[ldap_name]
    except (IndexError, KeyError):
        return field.default
    
    if schema.interfaces.IBool.providedBy(field):
        if value == 'True': return True
        elif value == 'False': return False
    if schema.interfaces.IPassword.providedBy(field):
        # passwords are never displayed
        return u''
    else:
        if not as_multi:
            return value[0]
        return value

