#!/usr/bin/env python

##########################################################################
#                                                                        #
#  This program is free software; you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation; version 2 of the License.               #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
##########################################################################

from datetime import datetime
import os
import sys
import re
import logging


## UTILS
from django.utils.encoding import smart_str

## PROJECT LIBS
from sonet.edgecache import EdgeCache
import sonet.mediawiki as mwlib
from sonet.lib import find_open_for_this_file
from sonet.timr import Timr

from collections import defaultdict

class HistoryPageProcessor(mwlib.PageProcessor):
    """
    HistoryPageProcessor extracts a graph from a meta-history or a
    stub-meta-history dump.

    A state-machine-like approach is used to parse the file.

    Only tag-end events are used. (eg. in <a><b></b></a> the first event is for
    the <b> tag, then the one for <a>).

    The entry point is process_title (one per page). Then, in every page there
    are many revisions, and each one has timestamp and contributor tags.

    <page>
        <title>Title</title>
        <revision>
            <timestamp>...<timestamp>
            <contributor>...</contributor>
        </revision>
        (... more revisions ...)
    </page>
    """
    # to limit the extraction to changes before a datetime
    time_end = None
    # to limit the extraction to changes after a datetime
    time_start = None
    counter_deleted = 0
    _re_welcome = None
    __welcome_pattern = None

    @property
    def welcome_pattern(self):
        return self.__welcome_pattern

    @welcome_pattern.setter
    def welcome_pattern(self, value):
        self.__welcome_pattern = value
        self._re_welcome = re.compile(value, flags=re.IGNORECASE)

    ## PAGE RELATED VARIABLES
    _receiver = None
    _skip = False

    ## REVISION RELATED VARIABLES
    _sender = None
    _skip_revision = False
    _time = None ## time of this revision
    _welcome = False

    def __init__(self, **kwargs):
        if 'ecache' not in kwargs:
            kwargs['ecache'] = EdgeCache()
        super(HistoryPageProcessor, self).__init__(**kwargs)

    def process_title(self, elem):
        self.delattr(("_counter", "_type", "_title", "_skip", "_date", "_receiver"))
        if self._skip_revision: return

        title = elem.text
        a_title = title.split(':')

        if len(a_title) > 1 and smart_str(a_title[0]) in self.user_talk_names:
            self._receiver = mwlib.normalize_pagename(a_title[1])
        else:
            self._skip = True
            return

        try:
            title.index('/')
            self.count_archive += 1
            self._skip = True
        except ValueError:
            pass
        finally:
            del title, a_title

    def process_timestamp(self, elem):
        if self._skip_revision: return

        timestamp = elem.text
        year = int(timestamp[:4])
        month = int(timestamp[5:7])
        day = int(timestamp[8:10])
        hour = int(timestamp[11:13])
        minutes = int(timestamp[14:16])
        seconds = int(timestamp[17:19])
        revision_time = datetime(year, month, day, hour, minutes, seconds)
        if ((self.time_end and revision_time > self.time_end) or
            (self.time_start and revision_time < self.time_start)):
            self._skip_revision = True
        else:
            self._time = revision_time

        del revision_time

    def process_contributor(self, contributor):
        if self._skip_revision: return

        if contributor is None:
            self._skip_revision = True

        sender_tag = contributor.find(self.tag['username'])
        if sender_tag is None:
            try:
                self._sender = contributor.find(self.tag['ip']).text
                if self._sender is None:
                    self._skip_revision = True
                    self.counter_deleted += 1
            except AttributeError:
                ## user deleted
                self._skip_revision = True
                self.counter_deleted += 1
        else:
            try:
                self._sender = mwlib.normalize_pagename(sender_tag.text)
            except AttributeError:
                ## if username is defined but empty, look for id tag
                try:
                    self._sender = contributor.find(self.tag['id']).text
                except KeyError:
                    self._skip_revision = True

    def process_revision(self, _):
        skip = self._skip_revision
        self._skip_revision = False
        welcome, self._welcome = self._welcome, False

        if skip: return

        assert self._sender is not None, "Sender still not defined"
        assert self._receiver is not None, "Receiver still not defined"
        self.ecache.add(self._receiver, {
            self._sender: [mwlib.Message(self._time, welcome),]
                           })
        self._sender = None
        self._time = None

    def process_page(self, _):
        if self._skip:
            self._skip = False
            return

        self.count += 1
        if not self.count % 500:
            print >> sys.stderr, self.count

    def delattr(self, attrs):
        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def process_comment(self, elem):
        if self._skip_revision: return
        if not self.__welcome_pattern: return
        assert self._welcome == False, 'processor._welcome is True!'
        #print elem.text.encode('utf-8')
        if not elem.text: return
        if self._re_welcome.search(elem.text):
            self._welcome = True

    def get_network(self):
        with Timr('Flushing'):
            self.ecache.flush()
        return self.ecache.get_network(edge_label='timestamp')

    def end(self):
        logging.info('TOTAL UTP: %d' % self.count)
        logging.info('ARCHIVES: %d' % self.count_archive)
        logging.info('DELETED: %d' % self.counter_deleted)


def save_graph(g, lang, type_, date_):

    counter = 0
    with Timr('Setting weight attribute on edges'):
        for e in g.es:
            e['weight'] = len(e['timestamp'])
            #e['timestamp'] = str(e['timestamp'])
            counter += 1
            if not counter % 10000:
                logging.debug(counter)

    with Timr('Pickling'):
        g.write("%swiki-%s%s.pickle" % (lang, date_, type_), format="pickle")
    #g.write("%swiki-%s%s.graphmlz" % (lang, date_, type_), format="graphmlz")

def opt_parse():
    from optparse import OptionParser
    from sonet.lib import SonetOption

    p = OptionParser(usage="usage: %prog [options] dumpfile",
                     option_class=SonetOption, description=
                     'Count edits on User Talk Pages and create a graph from '
                     'it. Save the graph as a pickled iGraph object.')
    p.add_option('-s', '--start', action="store",
        dest='start', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions starting from this date")
    p.add_option('-e', '--end', action="store",
        dest='end', type="yyyymmdd", metavar="YYYYMMDD", default=None,
        help="Look for revisions until this date")
    opts, args = p.parse_args()

    ## CHECK IF OPTIONS ARE OK
    if len(args) != 1:
        p.error("Wrong number of arguments")
    if not os.path.exists(args[0]):
        p.error("Dump file does not exist (%s)" % (args[0], ))
    return (opts, args)


def main():

    logging.basicConfig(#filename="graph_longiudinal_analysis.log",
                                stream=sys.stderr,
                                level=logging.DEBUG)
    logging.info('---------------------START---------------------')

    opts, args = opt_parse()
    xml = args[0]

    ## SET UP FOR PROCESSING
    lang, date_, type_ = mwlib.explode_dump_filename(xml)

    deflate, _lineno = find_open_for_this_file(xml)

    welcome = defaultdict(str)

    welcome.update({
        'it': r'Benvenut'
        ,'en': r'Welcome'
    })

    if _lineno:
        src = deflate(xml, 51)   # Read first 51 lines to extract namespaces
    else:
        src = deflate(xml)

    tag = mwlib.get_tags(src,
        tags='page,title,revision,timestamp,contributor,username,ip,comment')

    translations = mwlib.get_translations(src)

    try:
        lang_user = unicode(translations['User'])
        lang_user_talk = unicode(translations['User talk'])
    except UnicodeDecodeError:
        lang_user = smart_str(translations['User'])
        lang_user_talk = smart_str(translations['User talk'])

    assert lang_user, "User namespace not found"
    assert lang_user_talk, "User Talk namespace not found"

    src.close()
    src = deflate(xml)

    processor = HistoryPageProcessor(tag=tag,
        user_talk_names=(lang_user_talk, u"User talk"))
    processor.time_start = opts.start
    processor.time_end = opts.end
    processor.welcome_pattern = welcome[lang]

    with Timr('Processing'):
        processor.start(src) ## PROCESSING

    with Timr('Getting network'):
        g = processor.get_network()

    logging.info("Nodes: %d" % len(g.vs))
    logging.info("Edges: %d" % len(g.es))

    with Timr('Saving graph'):
        save_graph(g, lang, type_, date_)

if __name__ == "__main__":
    #import cProfile as profile
    #profile.run('main()', 'mainprof')
    main()
