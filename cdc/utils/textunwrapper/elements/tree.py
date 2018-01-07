"""
Text Block object implementation.
"""

import itertools
from enum import Enum, auto


class BlockType(Enum):
    """
    Semantic Block types
    """

    DOCUMENT_BLOCK          = auto()    # document element
    TEXT_BLOCK              = auto()    # unspecified text block
    WRAPPED_TEXT_BLOCK      = auto()    # text with wrapped content
    WHITESPACE_BLOCK        = auto()    # whitespace, no text

    # These types are used if the specific type of text has been identified
    PARAGRAPH_BLOCK         = auto()
    TABLE_BLOCK             = auto()
    ORDERED_LIST_BLOCK      = auto()
    UNORDERED_LIST_BLOCK    = auto()


class TextBlock():
    """
    Text Block object
    """

    def __init__(self, block_type):

        # TODO: validate input

        self.line_separator = "\n"

        self.type = block_type
        self.is_wrapped = False
        self.lines = []

        self._children = []


    def __len__(self):
        return len(self._children)

    def __getitem__(self, index):
        return self._children[index]

    def __setitem__(self, index, element):
        self._children[index] = element

    def __delitem__(self, index):
        del self._children[index]


    @property
    def block_count(self):
        """
        Number of sub-elements in block.
        """
        return len(self._children)


    @property
    def line_count(self):
        """
        Number of lines in block.
        """
        return len(self.line_lengths)

    @property
    def line_lengths(self):
        """
        Returns lengths of all lines in a list.
        """
        return [line.length for line in self.line_iter()]


    @property
    def indent(self):
        """
        Block-level indentation level.

        This is the smallest indentation across all lines.
        """
        return min([line.indent for line in self.lines])

    @property
    def max_line_length(self):
        """
        Returns length of longest raw line.
        """
        return max([line.length for line in self.line_iter()])

        
    def get_longest_line_length(self, line_type=None):
        """
        Returns length of longest raw line.
        """
        if line_type:
            return max([line.length for line in self.line_iter_by_type(line_type)])
        else:
            return max([line.length for line in self.line_iter()])

        
        
    @property
    def min_line_length(self):
        """
        Returns length of longest raw line.
        """
        return min([line.length for line in self.line_iter()])


    @property
    def stripped_str(self):
        """
        Block data as a single string with each line stripped.
        """
        return self.line_separator.join([line.str.strip() for line in self.lines])
        
    def __str__(self):
        """
        Block data as a single string.
        """
        return self.line_separator.join([line.str for line in self.lines])



    def __repr__(self):
        return "<%s %s line_count=%d indent=%d min_ll=%d max_ll=%d at %#x>" % (
                self.__class__.__name__, self.type, self.line_count, self.indent, self.min_line_length, self.max_line_length, id(self))


    def append(self, subelement):
        #self._assert_is_element(subelement)
        self._children.append(subelement)        


    def extend(self, elements):
        """Append subelements from a sequence.
        *elements* is a sequence with zero or more elements.
        """
        for element in elements:
            #self._assert_is_element(element)
            self._children.extend(elements)


    def transpose(self):

        if self.line_count < 2:
            return ""
        
        return self.line_separator.join( ["".join(l) for l in itertools.zip_longest(*(line.str for line in self.lines), fillvalue=" ")] )


    def line_iter(self):

        for line in self.lines:
            yield line

        for block in self._children:
            yield from block.line_iter()

            
    def line_iter_by_type(self, line_type):
        """
        Iterate over lines, only returning lines of the specified types.
        """

        for line in self.lines:
            if line.type & line_type:
                yield line

        for block in self._children:
            yield from block.line_iter_by_type(line_type)            



class Document(TextBlock):

    def __init__(self):

        #self.lines = []
        #self.text_blocks = []
        
        super().__init__(BlockType.DOCUMENT_BLOCK)


    def __str__(self):
        return "\n".join(map(str, self.lines))

    def __repr__(self):
        return "<%s block_count=%d max_ll=%d at %#x>" % (
                self.__class__.__name__, len(self), self.max_line_length, id(self))

        #return "\n".join(map(repr, self.lines))



