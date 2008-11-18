import re
import grok
import martian

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

def quote( value ):
    "Escape a string so it is safe for use in an LDAP Query"
    special_chars = '*()'
    value = value.replace('\\','\\\\') # ME NOT GROK BACKSLASHES
    for char in special_chars:
        value = value.replace(char, '\\%s' % char)
    return value

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

