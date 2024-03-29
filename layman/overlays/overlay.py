#!/usr/bin/python
# -*- coding: utf-8 -*-
################################################################################
# LAYMAN OVERLAY BASE CLASS
################################################################################
# File:       overlay.py
#
#             Base class for the different overlay types.
#
# Copyright:
#             (c) 2005 - 2009 Gunnar Wrobel
#             (c) 2009        Sebastian Pipping
#             (c) 2009        Christian Groschupp
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Gunnar Wrobel <wrobel@gentoo.org>
#             Sebastian Pipping <sebastian@pipping.org>
#             Christian Groschupp <christian@groschupp.org>
#
''' Basic overlay class.'''

__version__ = "0.2"

#===============================================================================
#
# Dependencies
#
#-------------------------------------------------------------------------------

import sys, re, os, os.path
import codecs
import locale
import xml.etree.ElementTree as ET # Python 2.5

from layman.utils import pad, terminal_width, get_encoding, encoder
from layman.compatibility import encode

from   layman.overlays.bzr       import BzrOverlay
from   layman.overlays.darcs     import DarcsOverlay
from   layman.overlays.git       import GitOverlay
from   layman.overlays.g_common  import GCommonOverlay
from   layman.overlays.mercurial import MercurialOverlay
from   layman.overlays.cvs       import CvsOverlay
from   layman.overlays.svn       import SvnOverlay
from   layman.overlays.rsync     import RsyncOverlay
from   layman.overlays.tar       import TarOverlay

#===============================================================================
#
# Constants
#
#-------------------------------------------------------------------------------

OVERLAY_TYPES = dict((e.type_key, e) for e in (
    GitOverlay,
    GCommonOverlay,
    CvsOverlay,
    SvnOverlay,
    RsyncOverlay,
    TarOverlay,
    BzrOverlay,
    MercurialOverlay,
    DarcsOverlay
))

QUALITY_LEVELS = 'core|stable|testing|experimental|graveyard'.split('|')

WHITESPACE_REGEX = re.compile('\s+')


class Overlay(object):
    ''' Derive the real implementations from this.'''

    def __init__(self, config, xml=None, ovl_dict=None,
        ignore = 0):
        '''
        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> import xml.etree.ElementTree as ET # Python 2.5
        >>> document =ET.parse(here + '/../tests/testfiles/global-overlays.xml')
        >>> overlays = document.findall('overlay') + document.findall('repo')
        >>> from layman.output import Message
        >>> output = Message()
        >>> a = Overlay({'output': output}, overlays[0])
        >>> a.name
        u'wrobel'
        >>> a.is_official()
        True
        >>> list(a.source_uris())
        [u'https://overlays.gentoo.org/svn/dev/wrobel']
        >>> a.owner_email
        u'nobody@gentoo.org'
        >>> a.description
        u'Test'
        >>> a.priority
        10
        >>> b = Overlay({'output': output}, overlays[1])
        >>> b.is_official()
        False
        '''
        self.config = config
        self.output = config['output']
        self._encoding_ = get_encoding(self.output)

        if xml is not None:
            self.from_xml(xml, ignore)
        elif ovl_dict is not None:
            self.from_dict(ovl_dict, ignore)


    def from_xml(self, xml, ignore):
        """Process an xml overlay definition
        """
        def strip_text(node):
            res = node.text
            if res is None:
                return ''
            return res.strip()

        _name = xml.find('name')
        if _name != None:
            self.name = encode(strip_text(_name))
        elif 'name' in xml.attrib:
            self.name = encode(xml.attrib['name'])
        else:
            raise Exception('Overlay from_xml(), "' + self.name + \
                'is missing a "name" entry!')

        _sources = xml.findall('source')
        # new xml format
        if _sources != []:
            _sources = [e for e in _sources if 'type' in e.attrib]
        #old xml format
        elif ('src' in xml.attrib) and ('type' in xml.attrib):
            s = ET.Element('source', type=xml.attrib['type'])
            s.text = xml.attrib['src']
            _sources = [s]
            del s

        def create_overlay_source(source_elem):
            _type = source_elem.attrib['type']
            try:
                _class = OVERLAY_TYPES[_type]
            except KeyError:
                raise Exception('Overlay from_xml(), "' + self.name + \
                    'Unknown overlay type "%s"!' % _type)
            _location = encode(strip_text(source_elem))
            return _class(parent=self, config=self.config,
                _location=_location, ignore=ignore)

        if not len(_sources):
            raise Exception('Overlay from_xml(), "' + self.name + \
                '" is missing a "source" entry!')

        _branch = xml.find('branch')
        if _branch != None:
            self.branch = encode(_branch.text.strip())
        elif 'branch' in xml.attrib:
            self.branch = encode(xml.attrib['branch'])
        else:
            self.branch = ''

        self.sources = [create_overlay_source(e) for e in _sources]

        _subpath = xml.find('subpath')
        if _subpath != None:
            self.subpath = encode(_subpath.text.strip())
        elif 'subpath' in xml.attrib:
            self.subpath = encode(xml.attrib['subpath'])
        else:
            self.subpath = ''

        _owner = xml.find('owner')
        if _owner == None:
            _email = None
        else:
            _email = _owner.find('email')
        if _owner != None and _email != None:
            self.owner_email = encode(strip_text(_email))
            _name = _owner.find('name')
            if _name != None:
                self.owner_name = encode(strip_text(_name))
            else:
                self.owner_name = None
        elif 'contact' in xml.attrib:
            self.owner_email = encode(xml.attrib['contact'])
            self.owner_name = None
        else:
            self.owner_email = ''
            self.owner_name = None
            if not ignore:
                raise Exception('Overlay  from_xml(), "' + self.name + \
                    '" is missing an "owner.email" entry!')
            elif ignore == 1:
                self.output.warn('Overlay "' + self.name + '" is missing a '
                         '"owner.email" entry!', 4)

        _desc = xml.find('description')
        if _desc != None:
            d = WHITESPACE_REGEX.sub(' ', strip_text(_desc))
            self.description = encode(d)
            del d
        else:
            self.description = ''
            if not ignore:
                raise Exception('Overlay  from_xml(), "' + self.name + \
                    '" is missing a description" entry!')
            elif ignore == 1:
                self.output.warn('Overlay "' + self.name + '" is missing a '
                         '"description" entry!', 4)

        if 'status' in xml.attrib:
            self.status = encode(xml.attrib['status'])
        else:
            self.status = None

        self.quality = u'experimental'
        if 'quality' in xml.attrib:
            if xml.attrib['quality'] in set(QUALITY_LEVELS):
                self.quality = encode(xml.attrib['quality'])

        if 'priority' in xml.attrib:
            self.priority = int(xml.attrib['priority'])
        else:
            self.priority = 50

        h = xml.find('homepage')
        l = xml.find('link')
        if h != None:
            self.homepage = encode(strip_text(h))
        elif l != None:
            self.homepage = encode(strip_text(l))
        else:
            self.homepage = None

        self.feeds = [encode(strip_text(e)) \
            for e in xml.findall('feed')]

        _irc = xml.find('irc')
        if _irc != None:
            self.irc = encode(strip_text(_irc))
        else:
            self.irc = None


    def from_dict(self, overlay, ignore):
        """Process an xml overlay definition
        """
        self.output.debug("Overlay from_dict(); overlay" + str(overlay))
        _name = overlay['name']
        if _name != None:
            self.name = encode(_name)
        else:
            raise Exception('Overlay from_dict(), "' + self.name +
                'is missing a "name" entry!')

        _sources = overlay['sources']

        if _sources == None:
            raise Exception('Overlay from_dict(), "' + self.name +
                '" is missing a "source" entry!')

        def create_dict_overlay_source(source_):
            _src, _type, _sub = source_
            try:
                _class = OVERLAY_TYPES[_type]
            except KeyError:
                raise Exception('Overlay from_dict(), "' + self.name +
                    'Unknown overlay type "%s"!' % _type)
            _location = encode(_src)
            return _class(parent=self, config=self.config,
                _location=_location, ignore=ignore)

        self.sources = [create_dict_overlay_source(e) for e in _sources]

        _owner = overlay['owner_name']
        if _owner == None:
            self.owner_name = None
            _email = None
        else:
            self.owner_name = encode(_owner)
            _email = overlay['owner_email']
        if _email != None:
            self.owner_email = encode(_email)
        else:
            self.owner_email = None
            if not ignore:
                raise Exception('Overlay from_dict(), "' + self.name +
                    '" is missing an "owner.email" entry!')
            elif ignore == 1:
                self.output.warn('Overlay from_dict(), "' + self.name +
                    '" is missing an "owner.email" entry!', 4)

        _desc = overlay['description']
        if _desc != None:
            d = WHITESPACE_REGEX.sub(' ', _desc)
            self.description = encode(d)
            del d
        else:
            self.description = ''
            if not ignore:
                raise Exception('Overlay from_dict(), "' + self.name +
                    '" is missing a "description" entry!')
            elif ignore == 1:
                self.output.warn('Overlay from_dict(), "' + self.name +
                    '" is missing a "description" entry!', 4)

        if overlay['status']:
            self.status = encode(overlay['status'])
        else:
            self.status = None

        self.quality = u'experimental'
        if len(overlay['quality']):
            if overlay['quality'] in set(QUALITY_LEVELS):
                self.quality = encode(overlay['quality'])

        if overlay['priority']:
            self.priority = int(overlay['priority'])
        else:
            self.priority = 50

        h = overlay['homepage']
        if h != None:
            self.homepage = encode(h)
        else:
            self.homepage = None

        self.feeds = [encode(e) \
            for e in overlay['feeds']]

        _irc = overlay['irc']
        if _irc != None:
            self.irc = encode(_irc)
        else:
            self.irc = None

        #xml = self.to_xml()
        # end of from_dict


    def __eq__(self, other):
        for i in ('description', 'homepage', 'name', 'owner_email',
                'owner_name', 'priority', 'status'):
            if getattr(self, i) != getattr(other, i):
                return False
        for i in self.sources + other.sources:
            if not i in self.sources:
                return False
            if not i in other.sources:
                return False
        return True


    def __ne__(self, other):
        return not self.__eq__(other)


    def set_priority(self, priority):
        '''Set the priority of this overlay.'''
        self.priority = int(priority)


    def to_xml(self):
        '''Convert to xml.'''
        repo = ET.Element('repo')
        if self.status != None:
            repo.attrib['status'] = self.status
        repo.attrib['quality'] = self.quality
        repo.attrib['priority'] = str(self.priority)
        name = ET.Element('name')
        name.text = self.name
        repo.append(name)
        desc = ET.Element('description')
        desc.text = self.description
        repo.append(desc)
        if self.homepage != None:
            homepage = ET.Element('homepage')
            homepage.text = self.homepage
            repo.append(homepage)
        if self.irc != None:
            irc = ET.Element('irc')
            irc.text = self.irc
            repo.append(irc)
        owner = ET.Element('owner')
        repo.append(owner)
        owner_email = ET.Element('email')
        owner_email.text = self.owner_email
        owner.append(owner_email)
        if self.owner_name != None:
            owner_name = ET.Element('name')
            owner_name.text = self.owner_name
            owner.append(owner_name)
        for i in self.sources:
            source = ET.Element('source', type=i.__class__.type_key)
            source.text = i.src
            repo.append(source)
            del source
        for i in self.sources:
            # NOTE: Two loops on purpose so the
            # hooks are called with all sources in
            i.to_xml_hook(repo)
        for i in self.feeds:
            feed = ET.Element('feed')
            feed.text = i
            repo.append(feed)
            del feed
        return repo


    def add(self, base):
        res = 1
        first_s = True
        for s in self.sources:
            if not first_s:
                self.output.info("\nTrying next source of listed sources...", 4)
            try:
                res = s.add(base)
                if res == 0:
                    # Worked, throw other sources away
                    self.sources = [s]
                    break
            except Exception, error:
                self.output.warn(str(error), 4)
            first_s = False
        return res


    def sync(self, base):
        self.output.debug("overlay.sync(); name = %s" % self.name, 4)
        assert len(self.sources) == 1
        return self.sources[0].sync(base)


    def delete(self, base):
        assert len(self.sources) == 1
        return self.sources[0].delete(base)


    def get_infostr(self):
        '''
        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> import xml.etree.ElementTree as ET # Python 2.5
        >>> document =ET.parse(here + '/../tests/testfiles/global-overlays.xml')
        >>> overlays = document.findall('overlay') + document.findall('repo')
        >>> from layman.output import Message
        >>> output = Message()
        >>> a = Overlay({'output': output}, overlays[0])
        >>> print a.get_infostr()
        wrobel
        ~~~~~~
        Source  : https://overlays.gentoo.org/svn/dev/wrobel
        Contact : nobody@gentoo.org
        Type    : Subversion; Priority: 10
        Quality : experimental
        <BLANKLINE>
        Description:
          Test
        <BLANKLINE>
        '''

        result = u''

        result += self.name + u'\n' + (len(self.name) * u'~')

        if len(self.sources) == 1:
            result += u'\nSource  : ' + self.sources[0].src
        else:
            result += u'\nSources:'
            for i, v in enumerate(self.sources):
                result += '\n  %d. %s' % (i + 1, v.src)
            result += '\n'

        if self.owner_name != None:
            result += u'\nContact : %s <%s>' \
                % (self.owner_name, self.owner_email)
        else:
            result += u'\nContact : ' + self.owner_email
        if len(self.sources) == 1:
            result += u'\nType    : ' + self.sources[0].type
        else:
            result += u'\nType    : ' + '/'.join(
                sorted(set(e.type for e in self.sources)))
        result += u'; Priority: ' + str(self.priority) + u'\n'
        result += u'Quality : ' + self.quality + u'\n'


        description = self.description
        description = re.compile(u' +').sub(u' ', description)
        description = re.compile(u'\n ').sub(u'\n', description)
        result += u'\nDescription:'
        result += u'\n  '.join((u'\n' + description).split(u'\n'))
        result += u'\n'

        if self.homepage != None:
            link = self.homepage
            link = re.compile(u' +').sub(u' ', link)
            link = re.compile(u'\n ').sub(u'\n', link)
            result += u'\nLink:'
            result += u'\n  '.join((u'\n' + link).split(u'\n'))
            result += u'\n'

        if self.irc != None:
            result += u'\nIRC : ' + self.irc + u'\n'

        if len(self.feeds):
            result += u'\n%s:' % ((len(self.feeds) == 1) and "Feed" or "Feeds")
            for i in self.feeds:
                result += u'\n  %s' % i
            result += u'\n'

        return encoder(result, self._encoding_)


    def short_list(self, width = 0):
        '''
        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> import xml.etree.ElementTree as ET # Python 2.5
        >>> document =ET.parse(here + '/../tests/testfiles/global-overlays.xml')
        >>> overlays = document.findall('repo') + document.findall('overlay')
        >>> from layman.output import Message
        >>> output = Message()
        >>> a = Overlay({'output': output}, overlays[0])
        >>> print a.short_list(80)
        wrobel                    [Subversion] (https://o.g.o/svn/dev/wrobel         )
        '''
        if len(self.name) > 25:
            name = self.name + "   ###\n"
            name += pad(" ", 25)
        else:
            name   = pad(self.name, 25)

        if len(set(e.type for e in self.sources)) == 1:
            _type = self.sources[0].type
        else:
            _type = '%s/..' % self.sources[0].type

        mtype  = ' [' + pad(_type, 10) + ']'
        if not width:
            width = terminal_width()-1
        srclen = width - 43
        source = ', '.join(self.source_uris())
        if len(source) > srclen:
            source = source.replace("overlays.gentoo.org", "o.g.o")
        source = ' (' + pad(source, srclen) + ')'

        return encoder(name + mtype + source, self._encoding_)


    def is_official(self):
        '''Is the overlay official?'''
        return self.status == 'official'


    def is_supported(self):
        return any(e.is_supported() for e in self.sources)


    def source_uris(self):
        for i in self.sources:
            yield i.src


    def source_types(self):
        for i in self.sources:
            yield i.type


#==============================================================================
#
# Testing
#
#------------------------------------------------------------------------------

if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__])
