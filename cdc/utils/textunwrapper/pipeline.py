"""

"""

from .elements.line import EOLType
from .elements.tree import BlockType


class Pipeline():
    """
    Represents a text parsing pipeline.

    """

    def __init__(self, **kwargs):
        """
        
        """

        self.loader = None      # Method to read the data
        self.transforms = []    # Ordered list of data transformation steps
        
        # Document rendering methods
        self.renderers = {
            'reflow': self.render_reflow,
            'linetype': self.render_linetype,
            'blocktype': self.render_blocktype,
        }
        
        return

    def put_info(self, msg):
        print(msg)

    def process(self, data):
        """
        Process the given data with the pipeline.
        """

        doc = self.loader(data)

        # Apply the transformations
        for transform in self.transforms:
            transform(doc)

        # Render it?

        return doc

    def render(self, doc, renderer):
        """
        Dispatch to the specified renderer.
        """
        return self.renderers[renderer](doc)

    def render_reflow(self, doc):
        """
        """
        
        EOL_MAP = {
            EOLType.SOFT: " ",      # This will join the next line
            EOLType.HARD: "\n",     # Hard break
        }
        
        
        #return "".join(line.str + EOL_MAP[line.eol] for line in doc.line_iter())
        
        text = ""

        # strip the lines after a soft break
        prev_eol = EOLType.HARD
        
        for line in doc.line_iter():
            text += (line.str.lstrip() if prev_eol == EOLType.SOFT else line.str) + EOL_MAP[line.eol]
            prev_eol = line.eol
        
        return text
        
        for block in doc:
            #print(block)

            if block.type == BlockType.WRAPPED_TEXT_BLOCK:
                text += block.lines[0].str + " " + " ".join([line.str.lstrip() for line in block.lines[1:]])  + "\n"
            else:
                text += str(block) + "\n"

        return text


    def render_linetype(self, doc):
        """
        """

        text = ""

        for block in doc:
            #print(block)
            for line in block.line_iter():
                text += "[%s] %s\n" % (line.type, line.str)

        return text
        
    def render_blocktype(self, doc):
        """
        """

        text = ""

        for block in doc:
            text += "[%s] %s\n" % (block.type, str(block))

        return text        
        
        
def window(iterable, left, right, padding=None, step=1 ):
    """Make a sliding window iterator with padding.
    
    Iterate over `iterable` with a step size `step` producing a tuple for each element:
        ( ... left items, item, right_items ... )
    such that item visits all elements of `iterable` `step`-steps aside, the length of 
    the left_items and right_items is `left` and `right` respectively, and any missing 
    elements at the start and the end of the iteration are padded with the `padding`
    item.
    For example:
    
    >>> list( window( range(5), 1, 2 ) )
    [(None, 0, 1, 2), (0, 1, 2, 3), (1, 2, 3, 4), (2, 3, 4, None), (3, 4, None, None)]
    """
    from itertools import islice, repeat, chain
    from collections import deque

    n = left + right + 1

    iterator = chain(iterable,repeat(padding,right)) 
    
    elements = deque( repeat(padding,left), n )
    elements.extend( islice( iterator, right - step + 1 ) )

    while True: 
        for i in range(step):
            elements.append( next(iterator) ) 
        yield tuple( elements )
        
        