from datetime import datetime 
from gum.interfaces import ILDAPEntry, IINetOrgPerson, IGroupOfUniqueNames 
from gum.interfaces import ITranscript, ITranscripts 
from hurry import query 
from hurry.query.query import Query 
from zope import interface 
from zope.container.interfaces import INameChooser 
import grok 

def uniqueMemberDiff(before, after):
    """
    Special diff logic for the uniqueMember attribute
    """
    before_uids = []
    after_uids = []
    for member in before:
        member = member.split(',')
        before_uids.append( member[0].split('=')[1] )
    for member in after:
        member = member.split(',')
        after_uids.append( member[0].split('=')[1] )
    before_uids = set(before_uids)
    after_uids = set(after_uids)
    return ( list(after_uids.difference(before_uids)),
             list(before_uids.difference(after_uids)), )


class Transcripts(grok.Container):
    interface.implements(ITranscripts)

    def sorted_by_date(self):
        return sorted( list( self.values() ) )


class Transcript(grok.Model):
    interface.implements(ITranscript)

    @property
    def user(self):
        app = grok.getApplication()
        try:
            uid = self.principal_id.split('.')[-1:][0]
            user = app['users'][ uid ]
        except KeyError:
            # non-ldap user, or user account was deleted
            class UnknownUser(object):
                def __init__(self, name):
                    self.uid = name
                    self.cn = name
            user = UnknownUser(uid)
        return user

    def diffs(self):
        """
        Compare the before and after entries and report differences
        as a List of Dictionaries. If the attributes are a single value
        the there are 'before' and 'after' keys in each Dict, for multi-value
        attributes such as 'uniqueMembers' an 'added' and 'removed' pair of
        keys is set:
        
        [ { 'attribute' : 'cn',
            'before' : 'GROK SMASH GROUP',
            'after' : 'ME GROK GROUP'},
          { 'attribute' : 'uniqueMembers',
            'added' : ['grok', 'mammoth'],
            'removed' : ['grok'] }
        ]
        
        """
        diffs = []
        # XXX i know, we are using the ZODB, so sorry for the cheesy eval()
        # uhm, some logic is not right here as well, we need to look at keys
        # in both the before and after sets :(
        if not self.before or not self.after:
            return []
        before = eval(self.before)
        # pfft!
        if not before:
            return []
        after = eval(self.after)
        for k,v in before.items():
            if k in ['objectClass','userPassword']:
                continue
            try:
                if k == 'uniqueMember':
                    added, removed = uniqueMemberDiff(
                        v, after['uniqueMember'] )
                    diffs.append( {'attribute' : k,
                                   'added' : added,
                                   'removed' : removed,
                                  }
                                )
                elif str(v) != str(after[k]):
                    diffs.append( { 'attribute' : k,
                                    'before' : before[k],
                                    'after' : after[k] }
                                 )
            except KeyError:
                pass
        return diffs

    def __cmp__(self, other):
        "Sorted by DateTime, newest to oldest"
        return cmp( other.observation_datetime, self.observation_datetime )


class Index(grok.View):
    grok.context(Transcripts)
    grok.name('index')
    grok.require(u'gum.View')

    def site(self):
        return grok.getApplication()


class TranscriptsByDN(grok.View):
    grok.context(Transcripts)
    grok.name('by-dn')
    grok.require(u'gum.View')

    def transcripts(self):        
        transcripts = Query().searchResults(
            query.Eq( ('gum_catalog', 'dn'), self.request.form['dn'] )
            )
        return transcripts


class TranscriptView(grok.View):
    grok.context(Transcript)
    grok.name('index')
    grok.require(u'gum.View')


@grok.subscribe(ILDAPEntry, grok.IObjectCreatedEvent)
def ldap_added_subscriber(obj, event):
    trst = Transcript()
    app = grok.getApplication()
    dbc = app.ldap_connection()
    trst.dn = obj.dn
    trst.before = u''
    trst.after = unicode(obj.ldap_entry)
    trst.observation_datetime = datetime.now()
    trst.principal_id = obj.principal_id
    namechooser = INameChooser( app['transcripts'] )
    name = namechooser.chooseName('ldap_add', trst)
    app['transcripts'][name] = trst


@grok.subscribe(ILDAPEntry, grok.IObjectModifiedEvent)
def ldap_modified_subscriber(obj, event):
    # XXX the way we jam principal.id into the temporary User object
    # works, but it don't feel right at all. Is there a way to look-up
    # the request from an event?!?
    trst = Transcript()
    app = grok.getApplication()
    dbc = app.ldap_connection()
    trst.dn = obj.dn
    try:
        trst.before = unicode(app['users'][obj.__name__].ldap_entry)
    except KeyError:
        trst.before = u''
    trst.after = unicode(obj.ldap_entry)
    trst.observation_datetime = datetime.now()
    trst.principal_id = obj.principal_id
    namechooser = INameChooser( app['transcripts'] )
    name = namechooser.chooseName('ldap_mod', trst)
    app['transcripts'][name] = trst
