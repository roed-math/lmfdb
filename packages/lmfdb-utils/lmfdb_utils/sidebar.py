"""
The sidebar menu, read from the YAML file named by the site's ``sidebar_file``
(see :class:`~lmfdb_utils.site.Site`).

The file maps keys (sorted to give the order of the sections) to sections::

    1intro:
      type: simple
      heading:
        title: Introduction
      parts:
        - title: Knowledge
          url_for: "knowledge.index"

Entries link to the endpoint given by ``url_for`` (with ``url_args``); an
entry with ``status: beta`` is only shown on beta, one with ``status: future``
is shown greyed out, and a section with ``users_only: true`` is only shown to
logged in users (and on beta).
"""
import yaml
from flask import url_for

from .site import current_site

def linked_name(item, level=""):
    """ take the dictionary describing a TOC entry and return the
    title wrapped in an appropriate href link.
    """
    if 'url_for' in item and not ('status' in item and item['status'] == 'future'):
        url = url_for(item['url_for'],**item.get('url_args',{}))
        this_entry = ''.join(['<a href="',url,'">',item['title'],'</a>'])
    else:
        this_entry = item['title']

    if this_entry == 'dummy':
        this_entry = '&nbsp;'

    if 'status' in item and item['status'] == 'future':
        this_entry = ''.join(['<div class="future">',this_entry,'</div>'])

    if 'status' in item and item['status'] == 'beta':
        this_entry = ''.join(['<div class="beta">', this_entry, '</div>'])

    # headings should be wrapped in h2's:
    if level == "heading":
        this_entry = ''.join(['<h2>', this_entry,'</h2>\n'])

    return this_entry

# The unique instance of the class SideBar:

the_sidebar = None

# Function to create the unique SideBar instance if necessary, and return it:

def get_sidebar():
    global the_sidebar
    if the_sidebar is None:
        the_sidebar = SideBar()
    return the_sidebar

# The SideBar class, created by reading the site's sidebar file

class SideBar():
    """
    Class for holding the sidebar content.
    """
    def __init__(self, filename=None):
        if filename is None:
            filename = current_site().sidebar_file
        if filename is None:
            self.toc_dic = {}
        else:
            with open(filename, encoding="utf-8") as F:
                self.toc_dic = yaml.load(F, Loader=yaml.FullLoader) or {}
        self.main_headings = list(self.toc_dic)
        self.main_headings.sort()
        def heading(k): return linked_name(self.toc_dic[k]['heading'],'heading')
        self.data = [(k,heading(k),self.toc_dic[k]) for k in self.main_headings]

        for _, _, data in self.data:
            if 'parts' in data:
                for entry in data['parts']:
                    entry['url'] = linked_name(entry)
                    if 'part2' in entry:
                        for pt2 in entry['part2']:
                            pt2['url'] = linked_name(pt2)
                            if 'part3' in pt2:
                                for item in pt2['part3']:
                                    item['url'] = linked_name(item)
