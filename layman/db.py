#!/usr/bin/python
# -*- coding: utf-8 -*-
#################################################################################
# LAYMAN OVERLAY DB
#################################################################################
# File:       db.py
#
#             Access to the db of overlays
#
# Copyright:
#             (c) 2005 - 2008 Gunnar Wrobel
#             Distributed under the terms of the GNU General Public License v2
#
# Author(s):
#             Gunnar Wrobel <wrobel@gentoo.org>
#
'''Handles different storage files.'''

from __future__ import with_statement

__version__ = "$Id: db.py 309 2007-04-09 16:23:38Z wrobel $"

#===============================================================================
#
# Dependencies
#
#-------------------------------------------------------------------------------

import os, os.path
import urllib2
import hashlib

from   layman.utils             import path, delete_empty_directory
from   layman.dbbase            import DbBase
from   layman.makeconf          import MakeConf
from   layman.version           import VERSION

#from   layman.debug             import OUT

#===============================================================================
#
# Class DB
#
#-------------------------------------------------------------------------------

class DB(DbBase):
    ''' Handle the list of local overlays.'''

    def __init__(self, config):

        self.config = config
        self.output = config['output']

        self.path = config['local_list']
        self.output.debug("DB.__init__(): config['local_list'] = %s" % self.path, 3)

        if config['nocheck']:
            ignore = 2
        else:
            ignore = 1

        quiet = int(config['quietness']) < 3

        DbBase.__init__(self,
                          config,
                          paths=[config['local_list'], ],
                          ignore=ignore,
                          quiet=quiet)

        self.output.debug('DB handler initiated', 6)

    # overrider
    def _broken_catalog_hint(self):
        return ''

    def add(self, overlay, quiet = False):
        '''
        Add an overlay to the local list of overlays.

        >>> write = os.tmpnam()
        >>> write2 = os.tmpnam()
        >>> write3 = os.tmpnam()
        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> from layman.config import OptionConfig
        >>> myoptions = {'local_list' :
        ...           here + '/tests/testfiles/global-overlays.xml',
        ...           'make_conf' : write2,
        ...           'nocheck'    : 'yes',
        ...           'storage'   : write3}

        >>> config = OptionConfig(myoptions)
        >>> config.set_option('quietness', 3)
        >>> a = DB(config)
        >>> config.set_option('local_list', write)
        >>> b = DB(config)
        >>> config['output'].set_colorize(False)

        >>> m = MakeConf(config, b.overlays)
        >>> m.path = write2
        >>> success = m.write()
        >>> success
        True

        # Commented out since it needs network access:

        # >>> b.add(a.select('wrobel-stable')) #doctest: +ELLIPSIS
        # * Running command "/usr/bin/rsync -rlptDvz --progress --delete --delete-after --timeout=180 --exclude="distfiles/*" --exclude="local/*" --exclude="packages/*" "rsync://gunnarwrobel.de/wrobel-stable/*" "/tmp/file.../wrobel-stable""...
        # >>> c = DbBase([write, ], dict())
        # >>> c.overlays.keys()
        # [u'wrobel-stable']

        # >>> m = MakeConf(config, b.overlays)
        # >>> [i.name for i in m.overlays] #doctest: +ELLIPSIS
        # [u'wrobel-stable']

        # >>> os.unlink(write)
        >>> os.unlink(write2)

        #>>> import shutil
        # >>> shutil.rmtree(write3)
        '''

        if overlay.name not in self.overlays.keys():
            result = overlay.add(self.config['storage'], quiet)
            if result == 0:
                if 'priority' in self.config.keys():
                    overlay.set_priority(self.config['priority'])
                self.overlays[overlay.name] = overlay
                self.write(self.path)
                if self.config['make_conf']:
                    make_conf = MakeConf(self.config, self.overlays)
                    make_ok = make_conf.add(overlay)
                    return make_ok
                return True
            else:
                mdir = path([self.config['storage'], overlay.name])
                delete_empty_directory(mdir, self.output)
                if os.path.exists(mdir):
                    self.output.error('Adding repository "%s" failed!'
                                ' Possible remains of the operation have NOT'
                                ' been removed and may be left at "%s".'
                                ' Please remove them manually if required.' \
                                % (overlay.name, mdir))
                    return False
                else:
                    self.output.error(
                        'Adding repository "%s" failed!' % overlay.name)
                    return False
        else:
            self.output.error('Repository "' + overlay.name +
                '" already in the local (installed) list!')
            return False


    def delete(self, overlay):
        '''
        Add an overlay to the local list of overlays.

        >>> write = os.tmpnam()
        >>> write2 = os.tmpnam()
        >>> write3 = os.tmpnam()
        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> from layman.config import OptionConfig
        >>> myoptions = {'local_list' :
        ...           here + '/tests/testfiles/global-overlays.xml',
        ...           'make_conf' : write2,
        ...           'nocheck'    : 'yes',
        ...           'storage'   : write3}

        >>> config = OptionConfig(myoptions)
        >>> config.set_option('quietness', 3)
        >>> a = DB(config)
        >>> config.set_option('local_list', write)
        >>> b = DB(config)
        >>> config['output'].set_colorize(False)

        >>> m = MakeConf(config, b.overlays)
        >>> m.path = here + '/tests/testfiles/make.conf'
        >>> m.read()
        True

        >>> m.path = write2
        >>> m.write()
        True

        # >>> b.add(a.select('wrobel-stable')) #doctest: +ELLIPSIS
        # * Running command "/usr/bin/rsync -rlptDvz --progress --delete --delete-after --timeout=180 --exclude="distfiles/*" --exclude="local/*" --exclude="packages/*" "rsync://gunnarwrobel.de/wrobel-stable/*" "/tmp/file.../wrobel-stable""...
        # >>> b.add(a.select('wrobel')) #doctest: +ELLIPSIS
        # * Running command "/usr/bin/svn co "https://overlays.gentoo.org/svn/dev/wrobel/" "/tmp/file.../wrobel""...
        # >>> c = DbBase([write, ], dict())
        # >>> c.overlays.keys()
        # [u'wrobel', u'wrobel-stable']

        # >>> b.delete(b.select('wrobel'))
        # >>> c = DbBase([write, ], dict())
        # >>> c.overlays.keys()
        # [u'wrobel-stable']

        # >>> m = MakeConf(config, b.overlays)
        # >>> [i.name for i in m.overlays] #doctest: +ELLIPSIS
        # [u'wrobel-stable']

        # >>> os.unlink(write)
        >>> os.unlink(write2)

        #>>> import shutil
        # >>> shutil.rmtree(write3)
        '''

        if overlay.name in self.overlays.keys():
            make_conf = MakeConf(self.config, self.overlays)
            overlay.delete(self.config['storage'])
            del self.overlays[overlay.name]
            self.write(self.path)
            make_conf.delete(overlay)
        else:
            self.output.error('No local overlay named "' + overlay.name + '"!')
            return False
        return True

    def sync(self, overlay_name, quiet = False):
        '''Synchronize the given overlay.'''

        overlay = self.select(overlay_name)
        result = overlay.sync(self.config['storage'], quiet)
        if result:
            raise Exception('Syncing overlay "' + overlay_name +
                            '" returned status ' + str(result) + '!' +
                            '\ndb.sync()')

#===============================================================================
#
# Class RemoteDB
#
#-------------------------------------------------------------------------------

class RemoteDB(DbBase):
    '''Handles fetching the remote overlay list.'''

    def __init__(self, config, ignore_init_read_errors=False):

        self.config = config
        self.output = config['output']

        self.proxies = {}

        if config['proxy']:
            self.proxies['http'] = config['proxy']
        elif os.getenv('http_proxy'):
            self.proxies['http'] = os.getenv('http_proxy')

        if self.proxies:
            proxy_handler = urllib2.ProxyHandler(self.proxies)
            opener = urllib2.build_opener(proxy_handler)
            urllib2.install_opener(opener)

        self.urls  = [i.strip() for i in config['overlays'].split('\n') if len(i)]

        paths = [self.filepath(i) + '.xml' for i in self.urls]

        if config['nocheck']:
            ignore = 2
        else:
            ignore = 0

        quiet = int(config['quietness']) < 3

        DbBase.__init__(self, config, paths=paths, ignore=ignore,
            quiet=quiet, ignore_init_read_errors=ignore_init_read_errors)

    # overrider
    def _broken_catalog_hint(self):
        return 'Try running "sudo layman -f" to re-fetch that file'

    def cache(self):
        '''
        Copy the remote overlay list to the local cache.

        >>> here = os.path.dirname(os.path.realpath(__file__))
        >>> cache = os.tmpnam()
        >>> myoptions = {'overlays' :
        ...           ['file://' + here + '/tests/testfiles/global-overlays.xml'],
        ...           'cache' : cache,
        ...           'nocheck'    : 'yes',
        ...           'proxy' : None}
        >>> from layman.config import OptionConfig
        >>> config = OptionConfig(myoptions)
        >>> config.set_option('quietness', 3)
        >>> a = RemoteDB(config)
        >>> a.cache()
        True
        >>> b = open(a.filepath(config['overlays'])+'.xml')
        >>> b.readlines()[24]
        '      A collection of ebuilds from Gunnar Wrobel [wrobel@gentoo.org].\\n'

        >>> b.close()
        >>> os.unlink(a.filepath(config['overlays'])+'.xml')

        >>> a.overlays.keys()
        [u'wrobel', u'wrobel-stable']
        '''
        has_updates = False
        for url in self.urls:

            filepath = self.filepath(url)
            mpath = filepath + '.xml'
            tpath = filepath + '.timestamp'

            # check when the cache was last updated
            # and don't re-fetch it unless it has changed
            request = urllib2.Request(url)
            opener = urllib2.build_opener()
            opener.addheaders = [('User-Agent', 'Layman-' + VERSION)]

            if os.path.exists(tpath):
                with open(tpath,'r') as previous:
                    timestamp = previous.read()
                request.add_header('If-Modified-Since', timestamp)

            if not self.check_path([mpath]):
                continue

            try:
                connection = opener.open(request)
                if 'last-modified' in connection.headers.keys():
                    timestamp = connection.headers['last-modified']
                elif 'date' in connection.headers.keys():
                    timestamp = connection.headers['date']
                else:
                    timestamp = None
            except urllib2.HTTPError, e:
                if e.code == 304:
                    self.output.info('Remote list already up to date: %s'
                        % url, 4)
                    self.output.info('Last-modified: %s' % timestamp, 4)
                else:
                    self.output.info('RemoteDB.cache(); HTTPError was:\n %s'
                        % str(e))
                continue
            except IOError, error:
                self.output.warn('RemoteDB.cache(); Failed to update the overlay list from: '
                         + url + '\nIOError was:\n' + str(error))
            else:
                if url.startswith('file://'):
                    quieter = 1
                else:
                    quieter = 0
                self.output.info('Fetching new list... %s' % url, 4 + quieter)
                if timestamp is not None:
                    self.output.info('Last-modified: %s' % timestamp, 4 + quieter)
                # Fetch the remote list
                olist = connection.read()

                # Create our storage directory if it is missing
                if not os.path.exists(os.path.dirname(mpath)):
                    try:
                        os.makedirs(os.path.dirname(mpath))
                    except OSError, error:
                        raise OSError('Failed to create layman storage direct'
                                      + 'ory ' + os.path.dirname(mpath) + '\n'
                                      + 'Error was:' + str(error))

                # Before we overwrite the old cache, check that the downloaded
                # file is intact and can be parsed
                try:
                    self.read(olist, origin=url)
                except Exception, error:
                    raise IOError('Failed to parse the overlays list fetched fr'
                                  'om ' + url + '\nThis means that the download'
                                  'ed file is somehow corrupt or there was a pr'
                                  'oblem with the webserver. Check the content '
                                  'of the file. Error was:\n' + str(error))

                # Ok, now we can overwrite the old cache
                try:
                    out_file = open(mpath, 'w')
                    out_file.write(olist)
                    out_file.close()

                    if timestamp is not None:
                        out_file = open(tpath, 'w')
                        out_file.write(str(timestamp))
                        out_file.close()

                    has_updates = True

                except Exception, error:
                    raise IOError('Failed to temporarily cache overlays list in'
                                  ' ' + mpath + '\nError was:\n' + str(error))
        return has_updates


    def filepath(self, url):
        '''Return a unique file name for the url.'''

        base = self.config['cache']

        self.output.debug('Generating cache path.', 6)

        return base + '_' + hashlib.md5(url).hexdigest()


    def check_path(self, paths, hint=True):
        '''Check for sufficient privileges'''
        self.output.debug('RemoteDB.check_path; paths = ' + str(paths), 8)
        is_ok = True
        for path in paths:
            if os.path.exists(path) and not os.access(path, os.W_OK):
                if hint:
                    self.output.warn(
                        'You do not have permission to update the cache (%s).'
                        % path)
                    import getpass
                    if getpass.getuser() != 'root':
                        self.output.warn('Hint: You are not root.\n')
                is_ok = False
        return is_ok

#===============================================================================
#
# Testing
#
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    import doctest, sys

    # Ignore warnings here. We are just testing
    from warnings     import filterwarnings, resetwarnings
    filterwarnings('ignore')

    doctest.testmod(sys.modules[__name__])

    resetwarnings()
