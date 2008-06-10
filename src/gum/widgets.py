import grok
from zope.component import getMultiAdapter
from zope.app.form.interfaces import IInputWidget
from zope.app.form.browser.widget import SimpleInputWidget
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

class AjaxUserChooserWidget(SimpleInputWidget):
    
    def _getFormInput(self):
        value = super(AjaxUserChooserWidget, self)._getFormInput()
        # Make sure that we always retieve a list object from the request
        # even for empty or single items
        if value is None:
            value = []
        if not isinstance(value, list):
            value = [value]
        return value
    
    def hasInput(self):
        return (self.name + '.marker') in self.request.form
    
    def hidden(self):
        s = ''
        for value in self._getFormValue():
            widget = getMultiAdapter( 
                (self.context.value_type, self.request), IInputWidget
            )
            widget.name = self.name
            widget.setRenderedValue(value)
            s += widget.hidden()
        return s

    __call__ = ViewPageTemplateFile('ajaxuserchooserwidget.pt')
