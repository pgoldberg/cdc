"""
UCProp related utilities.
"""

def get_ucprop(proplist, flag):
    """Get a UCProp element by flag"""
    return next((i for i in proplist if i['flag'] == flag), None)

def update_ucprop(proplist, flag, values):
    """Update a UCProp element by flag"""
    prop = get_ucprop(proplist, flag)
    
    if prop:
        prop.update(values)

    
    
class UCPropMixin:
    """
    UCProp related variables and members.
    """
    
    # Static UC_PROPS list
    UC_PROPS = []
