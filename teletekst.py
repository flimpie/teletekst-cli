from bs4 import BeautifulSoup, element
from enum import Enum
import string
from termcolor import colored
import re
import unicodedata
import html

def nos_pua_to_unicode(c):
    # 0xf0VH
    # where V is vertical in the G1 mosaic table on https://en.wikipedia.org/wiki/Teletext_character_set
    # and H is horizontal
    c_hex = ord(c)
    tt_map = {0xf020: ' ', 0xf021: '🬀', 0xf022: '🬁', 0xf023: '🬂', 0xf024: '🬃', 0xf025: '🬄', 0xf026: '🬅', 0xf027: '🬆', 0xf028: '🬇', 0xf029: '🬈', 0xf02a: '🬉', 0xf02b: '🬊', 0xf02c: '🬋', 0xf02d: '🬌', 0xf02e: '🬍', 0xf02f: '🬎',
              0xf030: '🬏', 0xf031: '🬐', 0xf032: '🬑', 0xf033: '🬒', 0xf034: '🬓', 0xf035: '▌', 0xf036: '🬔', 0xf037: '🬕', 0xf038: '🬖', 0xf039: '🬗', 0xf03a: '🬘', 0xf03b: '🬙', 0xf03c: '🬚', 0xf03d: '🬛', 0xf03e: '🬜', 0xf03f: '🬝',
              0xf060: '🬞', 0xf061: '🬟', 0xf062: '🬠', 0xf063: '🬡', 0xf064: '🬢', 0xf065: '🬣', 0xf066: '🬤', 0xf067: '🬥', 0xf068: '🬦', 0xf069: '🬧', 0xf06a: '▐', 0xf06b: '🬨', 0xf06c: '🬩', 0xf06d: '🬪', 0xf06e: '🬫', 0xf06f: '🬬',
              0xf070: '🬭', 0xf071: '🬮', 0xf072: '🬯', 0xf073: '🬰', 0xf074: '🬱', 0xf075: '🬲', 0xf076: '🬳', 0xf077: '🬴', 0xf078: '🬵', 0xf079: '🬶', 0xf07a: '🬷', 0xf07b: '🬸', 0xf07c: '🬹', 0xf07d: '🬺', 0xf07e: '🬻', 0xf07f: '█'}
    if c_hex in tt_map:
        return tt_map[c_hex]
    else:
        return c

def sub_nos_pua(inputString):
    for idx, c in enumerate(inputString):
        inputString = inputString[:idx] + nos_pua_to_unicode(c) + inputString[idx + 1:]
    return inputString
    

class TeletekstColour(Enum):
    BLACK = 0 #whatever this may mean
    RED = 1
    GREEN = 2
    BLUE = 3
    CYAN = 4
    YELLOW = 5
    WHITE = 6

    @staticmethod
    def from_str(label):
        if label in ('red', 'bg-red'):
            return TeletekstColour.RED
        elif label in ('green', 'bg-green'):
            return TeletekstColour.GREEN
        elif label in ('blue', 'bg-blue'):
            return TeletekstColour.BLUE
        elif label in ('cyan', 'bg-cyan'):
            return TeletekstColour.CYAN
        elif label in ('yellow', 'bg-yellow'):
            return TeletekstColour.YELLOW
        elif label in ('white', 'bg-white'):
            return TeletekstColour.WHITE
        elif label == "":
            return TeletekstColour.WHITE
        else:
            raise NotImplementedError


FG_MAP = {"red": TeletekstColour.RED, "green": TeletekstColour.GREEN, "blue": TeletekstColour.BLUE, "cyan": TeletekstColour.CYAN, "yellow": TeletekstColour.YELLOW}
BG_MAP = {"bg-red": TeletekstColour.RED, "bg-green": TeletekstColour.GREEN, "bg-blue": TeletekstColour.BLUE, "bg-cyan": TeletekstColour.CYAN, "bg-yellow": TeletekstColour.YELLOW}


class TeletekstPage():
    # we're storing page ID's as strings as sub-pages (i.e. "100-2") are not numeric
    prevPage = None
    nextPage = None
    nextSubPage = None
    prevSubPage = None
    fastTextLinks = [] # list of tuples, tuple being (pageId, name)
    pageContent = [] # list of lists, one top-level list is one line and those lines consist of instances of TeletekstString

    def __init__(self, ttJson = None):
        if ttJson:
            if ttJson['prevPage'] != "":
                self.prevPage = ttJson['prevPage']
            if ttJson['nextPage'] != "":
                self.nextPage = ttJson['nextPage']
            if ttJson['nextSubPage'] != "":
                self.nextSubPage = ttJson['nextSubPage']
            if ttJson['prevSubPage'] != "":
                self.prevSubPage = ttJson['prevSubPage']
            
            for fastTextLink in ttJson['fastTextLinks']:
                self.fastTextLinks.append((fastTextLink['title'], fastTextLink['page']))

            # bs4 cuts off preceding spaces from ttJson['content'], parse them out of the HTML manually
            pre_html_content = re.search(r"^(.*?)<", ttJson['content']).group(1) # ew
            
            content_replaced = ttJson['content'].replace("<span", "<pre")
            content_replaced = content_replaced.replace("</span", "</pre")
            

            # Yes, I was initially using BeautifulSoup for this.
            # For projects like this, you should.
            # The only problem is that BS4 uses lxml, and lxml collapses whitespace.
            # We want to preserve that whitespace.
            # Sadly, this is the only option for that.
            content_lines = ttJson['content'].split("\n")
            
            lineIndex = 1
            for content_line in content_lines:
                currentLine = []
                if content_line == "":
                    continue
                content_line = html.unescape(content_line)
                # just split it up in the pre-any-tag content and the rest
                line_parse_first_stage = re.search(r"^(.*?)(<.*)$", content_line)
                if not line_parse_first_stage:
                    # no tags for this whole line, parse as white on black
                    self.pageContent.append([TeletekstString(sub_nos_pua(content_line), TeletekstColour.BLACK, TeletekstColour.WHITE)])
                    continue

                html_content = line_parse_first_stage.groups()[1]
                # add the pre-anything content to currentLine
                currentLine.append(TeletekstString(sub_nos_pua(line_parse_first_stage.groups()[0]), TeletekstColour.BLACK, TeletekstColour.WHITE))


                # we have to run the same regex twice, basically.
                # once to find the space between the spans, and once to find the spans.
                # yeah it's weird, i am parsing HTML in regex, what about it?
                line_parse_find_spans_iter = re.finditer(r'<span ?c?l?a?s?s?=?"?(.*?)"?>.*?<\/span>', html_content)
                count = -1
                matchcount = 0 # don't ask
                whitespace_idx_start = None
                whitespace_idx_end = None
                whitespace_after = {} # will contain index of match, and what the content thereafter contains
                for match in line_parse_find_spans_iter:
                    if count == -1:
                        whitespace_idx_start = match.end()
                    else:
                        whitespace_idx_end = match.start()
                        if whitespace_idx_start != whitespace_idx_end:
                            whitespace_after[matchcount- 1] = html_content[whitespace_idx_start:whitespace_idx_end]
                            # minus one because we want to edit the line BEFORE
                        whitespace_idx_start = match.end() # TODO potential off-by-one here
                    count += 1
                    matchcount += 1

                # now, find all the spans in the remainder and add them to the current line
                matchcount = 0
                line_parse_find_spans = re.findall(r'<span ?c?l?a?s?s?=?"?(.*?)"?>(.*?)<\/span>', html_content)
                for span_match in line_parse_find_spans:
                    bgcolour = TeletekstColour.BLACK
                    fgcolour = TeletekstColour.WHITE

                    span_classes, span_content = span_match
                    span_classes = span_classes.rstrip().split(' ')
                    # remove any whitespace from the end of the classes and split them to get the individual classes

                    # very bodgily remove links, since we're in a terminal we can't do anything with them anyway
                    span_content = re.sub(r'<a class=".*?" href=".*?">(.*?)<\/a>', '\\1', span_content)
                    span_content = re.sub(r'<a id="fastText.*?" class=".*?" href=".*?">(.*)<\/a>', '\\1', span_content)
                    # set the bg and fg color based on the classes
                    for cl in span_classes:
                        if cl.startswith("bg"):
                            bgcolour = TeletekstColour.from_str(cl)
                        else:
                            fgcolour = TeletekstColour.from_str(cl)
                    currentLine.append(TeletekstString(sub_nos_pua(span_content), bgcolour, fgcolour))
                    if matchcount in whitespace_after:
                        currentLine.append(TeletekstString(sub_nos_pua(whitespace_after[matchcount]), TeletekstColour.BLACK, TeletekstColour.WHITE))
                    matchcount += 1
                lineIndex += 1
                self.pageContent.append(currentLine)
            
                    
                
    def printPageContent(self):
        for ttLine in self.pageContent:
            
            for ttString in ttLine:
                print(ttString.stringPrintable(), end='')
            print()
    
    def printPageGuide(self):
        # which one is the next/previous page or next/previous subpage
        nP = "   "
        pP = "   "
        if self.nextPage:
            nP = self.nextPage
        if self.prevPage:
            pP = self.prevPage
        print(colored(f'< {pP}    {nP} >', attrs=['bold']))
        if self.nextSubPage or self.prevSubPage:
            nS = "      "
            pS = "      "
            if self.nextSubPage:
                nS = self.nextSubPage
            if self.prevSubPage:
                nS = self.nextSubPage
            print(colored(f'< {pS}    {nS} >', attrs=['bold']))

            
           

                

class TeletekstString():
    body = None
    background = None
    foreground = None

    def __init__(self, body: string, background: TeletekstColour, foreground: TeletekstColour):
        self.body = body
        self.background = background
        self.foreground = foreground
    
    def __repr__(self):
        return f"<teletekst.TeletekstString '{self.body}', bg {self.background}, fg {self.foreground}>"
    
    def stringPrintable(self):
        return colored(self.body, self.foreground.name.lower(), f"on_{self.background.name.lower()}")

