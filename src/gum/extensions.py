import grok
from zope import component
from gum.interfaces import IExtensionMaker


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
        del self.context[name]
        
        return self.redirect(self.url(self.context))
