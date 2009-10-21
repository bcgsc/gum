from gum.interfaces import IExtensionMaker 
from zope import component 
import grok 

class Extensions(grok.Container):
    
    def installed(self):
        "List of installed extensions"
        return self.values()
    
    def is_installed(self, ext):
        "Return True if an extension is already installed"
        for installed_ext in self.values():
            if type(installed_ext) == type(ext):
                return True
        return False
    
    def available(self):
        "List of uninstalled extensions"
        return [
            ext_maker[1].new()
            for ext_maker in component.getUtilitiesFor(IExtensionMaker)
            if not self.is_installed(ext_maker[1].new())
        ]


class ExtensionsIndex(grok.View):
    grok.context(Extensions)
    grok.name('index')
    grok.require(u'gum.View')

    def get_ext_name(self, ext):
        # TODO: this could be fragile, a better way?
        return getattr(ext, 'grokcore.component.directive.name')


class Add(grok.View):
    grok.require(u'gum.Edit')
    
    def render(self, name):
        ext_maker = component.getUtility(IExtensionMaker, name)
        ext = ext_maker.new()
        self.context[name] = ext
        
        return self.redirect(self.url(ext, 'edit'))


class Delete(grok.View):
    grok.require(u'gum.Edit')
    
    def render(self, name):
        
        # handle deletions of broken objects
        # (there is perhaps a better way to do this than fiddling w/ the fixing_up attr?)
        import zope.app.container.contained
        zope.app.container.contained.fixing_up = True
        del self.context[name]
        zope.app.container.contained.fixing_up = False
        
        return self.redirect(self.url(self.context))
