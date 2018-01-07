import sys, copy
import math
import itertools

#import numpy as np


from .pipeline import Pipeline, window
from .elements.line import Line, LineType, EOLType
from .elements.tree import Document, TextBlock, BlockType

SEPARATOR_LINE_CHARS = set("_-=*~+#")

class RuleBasedUnwrapper(Pipeline):
    """
    
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.loader = self.load

        self.transforms.append(block_id)
        self.transforms.append(line_unwrap)

    def load(self, data):
        """
        Simple line-based loader
        """
        #self.put_info("loading...")

        def add_current_block():
            if current_block.line_count:
                doc.append(current_block)

        # Initialize document and current text block
        doc = Document()
        current_block = TextBlock(BlockType.TEXT_BLOCK)

        # Process all the lines and parse the blocks
        for line in data.splitlines():
            line_obj = Line(line)
            #print(repr(line_obj))

            if line_obj.type == LineType.BLANK_LINE:
                if current_block.type != BlockType.WHITESPACE_BLOCK:
                    add_current_block()
                    current_block = TextBlock(BlockType.WHITESPACE_BLOCK)
                
                current_block.lines.append(line_obj)

            else:
                if current_block.type != BlockType.TEXT_BLOCK:
                    add_current_block()
                    current_block = TextBlock(BlockType.TEXT_BLOCK)
                
                current_block.lines.append(line_obj)

        # add the last block
        add_current_block()

        #print(len(doc), "blocks loaded")
        #print(repr(doc))
        return doc


def block_id(doc):

    if doc.line_count < 2:
        return
        
    doc_longest_line = doc.get_longest_line_length(LineType.CONTENT)

    # Check for wrapping at the document level

    # Examine the top N lines clone to the longest line
    #doc_line_lengths = np.array(doc.line_lengths)

    #
    # Get the indicies of the lines
    #
    #doc_longest_lines = np.where(doc_line_lengths > (doc_longest_line - 9))[0]
    doc_longest_lines = [i for i, length in enumerate(doc.line_lengths) if length > (doc_longest_line - 9)]
    #print(doc_longest_lines)

    if len(doc_longest_lines) < 2:
        return  # can't be wrapped with 1 or no lines

    lines = list(doc.line_iter())
    num_potential_wraps = 0

    for line_num in doc_longest_lines:
        try:
            if len(lines[line_num].str + " " + lines[line_num+1].first_token) >= doc_longest_line:
                num_potential_wraps += 1
        except IndexError:
            continue

    #print("Potential wraps:", num_potential_wraps, "of", len(doc_longest_lines), "longest:", doc_longest_line)

    if num_potential_wraps / len(doc_longest_lines) > 0.55:
        doc.is_wrapped = True

    return


def line_unwrap(doc):
    """
    """

    if not doc.is_wrapped:
        return

    longest_line = doc.max_line_length

    for line in window(doc.line_iter(), 1, 1):

        # Skip blanks
        if line[1].type == LineType.BLANK_LINE or line[2] is None:
            continue

        # Tablulated or aligned lines
        if line[1].str.strip().count("   ") > 1 or line[1].str.strip().count("  ") > 2:
            continue
            
        # Separator lines
        line_chars = set(line[1].str)
        line_chars_count = len(line_chars)
        
        if line_chars_count > 0 and len(line_chars.intersection(SEPARATOR_LINE_CHARS)) / line_chars_count > 0.45:
            #print("###", line[1].str)
            continue
        
        # Check that the next line is not a list item


        # Check if the first word of the next line would fit
        if len(line[1].str + " " + line[2].first_token) >= longest_line:
            #print(">>>", line[1])
            #line[1].str += "   X"
            line[1].eol = EOLType.SOFT
            


def run(input_text):
    pipe = RuleBasedUnwrapper()
    doc = pipe.process(input_text)
    
    print("Rendering")
    reflowed = pipe.render(doc, "reflow")
    print(reflowed)

    return

        
if __name__ == "__main__":
    # read test data
    datafile = sys.argv[1] if len(sys.argv) > 1 else "data.txt"
    note_text = open(datafile).read()

    run(note_text)        