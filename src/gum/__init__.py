import re
import grok

class Add(grok.Permission):
    grok.name(u'gum.Add')

class Edit(grok.Permission):
    grok.name(u'gum.Edit')

class EditGroup(grok.Permission):
    grok.name(u'gum.EditGroup')

class Manager(grok.Permission):
    grok.name('zope.Manager')

def getProperty( data, name, default ):
    "Read a property from the raw LDAP data structure"
    try:
        return data[name][0]
    except (IndexError, KeyError):
        return default

def quote( value ):
    "Escape a string so it is safe for use in an LDAP Query"
    special_chars = '*()'
    value = value.replace('\\','\\\\') # ME NOT GROK BACKSLASHES
    for char in special_chars:
        value = value.replace(char, '\\%s' % char)
    return value
