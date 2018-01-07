"""
Line object implementation.
"""

from enum import Enum, Flag, auto

class LineType(Flag):
    """
    Semantic line types.
    """

    BLANK_LINE              = auto()

    TEXT_LINE               = auto()
    HEADING_LINE            = auto()
    HRULE_LINE              = auto()
    LIST_ITEM_LINE          = auto()
    TABLE_ROW_LINE          = auto()
    KEY_VALUE_LINE          = auto()

    # Flag Combination
    CONTENT = TEXT_LINE | HEADING_LINE | HRULE_LINE


class EOLType(Enum):
    """
    End-of-line types.
    """

    SOFT = auto()
    HARD = auto()


class Line():
    """
    """

    def __init__(self, line_str, line_type=None, *args, **extra):

        # Tabs to spaces
        self.str = line_str.rstrip().expandtabs(4)
        
        # Line type
        if not line_type:
            line_type  = LineType.BLANK_LINE if not self.str.strip() else LineType.TEXT_LINE

        self.type = line_type
        
        self.eol = EOLType.HARD

    @property
    def length(self):
        return len(self.str)

    @property
    def indent(self):
        return self.length - len(self.str.lstrip())

    @property
    def first_token(self):
        return self.str.split()[0] if self.type != LineType.BLANK_LINE else ""

    def __str__(self):
        return self.str

    def __repr__(self):
        return "<%s %s indent=%d at %#x data='%s'>" % (self.__class__.__name__, self.type, self.indent, id(self), self.str)


        


