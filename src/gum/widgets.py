import grok
import zope.component
import zope.formlib.interfaces
import zope.formlib.textwidgets
import zope.formlib.widget
import zope.pagetemplate.pagetemplatefile

class AjaxUserChooserWidget(zope.formlib.widget.SimpleInputWidget):
    
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
            widget = zope.component.getMultiAdapter( 
                (self.context.value_type, self.request), zope.formlib.interfaces.IInputWidget
            )
            widget.name = self.name
            widget.setRenderedValue(value)
            s += widget.hidden()
        return s

    def __call__(self):
        # a better way to do this? this broke during the Grok 1.1 to 1.3 upgrade
        # and the code below works but could be simpler?
        namespace = {}
        namespace['context'] = self.context
        namespace['request'] = self.request
        namespace['view'] = self
        return zope.pagetemplate.pagetemplatefile.PageTemplateFile(
            'ajaxuserchooserwidget.pt').pt_render(namespace,)

class LongTextWidget(zope.formlib.textwidgets.TextWidget):
    # make the default length 35 instead of 20
    displayWidth = 35
