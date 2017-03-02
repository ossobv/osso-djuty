# vim: set ts=8 sw=4 sts=4 et ai:

try:
    # If OutputWrapper is defined the output is automatically wrapped.
    from django.core.management.base import OutputWrapper as RealOutputWrapper

    def OutputWrapper(out):
        return out
except ImportError:  # Django<1.5
    # The output is not wrapped by default.
    # This version of smart_str does not keep lazy objects.
    from django.utils.encoding import smart_str as force_str

    class OutputWrapper(object):
        '''
        Wrapper around stdout/stderr, copied from Django 1.10.
        '''
        @property
        def style_func(self):
            return self._style_func

        @style_func.setter
        def style_func(self, style_func):
            if style_func and self.isatty():
                self._style_func = style_func
            else:
                self._style_func = lambda x: x

        def __init__(self, out, style_func=None, ending='\n'):
            self._out = out
            self.style_func = None
            self.ending = ending

        def __getattr__(self, name):
            return getattr(self._out, name)

        def isatty(self):
            return hasattr(self._out, 'isatty') and self._out.isatty()

        def write(self, msg, style_func=None, ending=None):
            ending = self.ending if ending is None else ending
            if ending and not msg.endswith(ending):
                msg += ending
            style_func = style_func or self.style_func
            self._out.write(force_str(style_func(msg)))

    RealOutputWrapper = OutputWrapper

__all__ = ['OutputWrapper']
