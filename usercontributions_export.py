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

from sonet.models import get_contributions_table
from sqlalchemy import select, func

import logging
import time
import sys
from base64 import b64decode
from zlib import decompress
from wbin import deserialize

from django.utils.encoding import smart_str

import sonet.mediawiki as mwlib
from sonet.lib import find_open_for_this_file, yyyymmdd_to_datetime


def user_iter(lang='en', paginate=10000000):
    contrib, conn = get_contributions_table()

    count_query = select([func.count(contrib.c.id)],
               contrib.c.lang == lang)
    s = select([contrib],
                contrib.c.lang == lang).order_by(
                    contrib.c.id).limit(paginate)

    count = conn.execute(count_query).fetchall()[0][0]

    #print >>sys.stderr, 'PAGES:', count

    for offset in xrange(0, count, paginate):
        rs = conn.execute(s.offset(offset))
        for row in rs:
            ## row is a RowProxy object: supports dict and list methods
            ## convert it to dict to use with csv.DictWriter
            v = dict(row)
            del v['id']
            del v['lang']
            v['namespace_edits'] = deserialize(decompress(b64decode(
                v['namespace_edits']
            ))) if v['namespace_edits'] is not None else None
            yield v


def prepare_data(namespaces, lang, date_, threshold=0):
    for user in user_iter(lang=lang):

        if user['normal_edits']:
            user['tot_edits'] = user['normal_edits']
            user['diversity_score'] = 1
        else:
            user['tot_edits'] = 0
            user['diversity_score'] = 0

        if user['namespace_edits'] is None:
            user['namespace_edits'] = [0, ] * len(namespaces)

        for i, namespace_edit in enumerate(user['namespace_edits']):
            user[namespaces[i]] = namespace_edit
            user['tot_edits'] += namespace_edit
            if namespace_edit:
                user['diversity_score'] += 1

        del user['namespace_edits']

        if user['tot_edits'] < threshold:
            continue

        ## smart_str to manage unicode
        user['username'] = smart_str(user['username'])

        user['days_since_first_edit'] = (date_ - user['first_edit']).days
        user['left_since'] = (date_ - user['last_edit']).days
        user['active_days'] = (user['last_edit'] - user['first_edit']).days

        user['first_edit_year'] = user['first_edit'].year
        user['first_edit_month'] = user['first_edit'].month
        user['first_edit_day'] = user['first_edit'].day
        user['last_edit_year'] = user['last_edit'].year
        user['last_edit_month'] = user['last_edit'].month
        user['last_edit_day'] = user['last_edit'].day

        ## converts datetime objects to timestamps (seconds elapsed since
        ## 1970-01-01)
        user['first_edit'] = int(time.mktime(user['first_edit'].timetuple()))
        user['last_edit'] = int(time.mktime(user['last_edit'].timetuple()))

        yield user


def create_option_parser():
    import argparse

    p = argparse.ArgumentParser(
        description='Export User contribution data from database into csv')

    ## optional parameters
    p.add_argument('-t', '--threshold',
                   help='total edits threshold (default: %(default)s)',
                   type=int, default=0)
    ## positional arguments
    p.add_argument('dump', help="dump file", metavar="DUMP_FILE")
    p.add_argument('out', help="output file (bz2 ext)", metavar="OUTPUT_FILE")

    return p

def main():
    from bz2 import BZ2File
    from csv import DictWriter

    logging.basicConfig(#filename="usercontributions_export.log",
                        stream=sys.stderr,
                        level=logging.DEBUG)
    logging.info('---------------------START---------------------')

    op = create_option_parser()
    args = op.parse_args()

    xml, out, threshold = args.dump, args.out, args.threshold

    lang, date_, _ = mwlib.explode_dump_filename(xml)
    deflate, _lineno = find_open_for_this_file(xml)

    date_ = yyyymmdd_to_datetime(date_, 1)

    if _lineno:
        src = deflate(xml, 51)   # Read first 51 lines to extract namespaces
    else:
        src = deflate(xml)

    namespaces = [v for _, v in mwlib.get_namespaces(src)]

    fout = BZ2File(out, 'w')

    fields = ['username', 'normal_edits', 'comments_count', 'comments_avg',
              'minor', 'revert', 'npov', 'welcome', 'please', 'thanks',
              'first_edit', 'last_edit', 'tot_edits', 'active_days',
              'days_since_first_edit', 'left_since', 'diversity_score',
              'first_edit_year', 'first_edit_month', 'first_edit_day',
              'last_edit_year', 'last_edit_month', 'last_edit_day', ]
    fields[2:2] = namespaces
    dw = DictWriter(fout, fields)
    dw.writeheader()

    ## to get only the first 1000 users:
    #from itertools import islice
    #data_iterator = islice(prepare_data(namespaces), 1000)
    data_iterator = prepare_data(namespaces, lang, date_, threshold)

    count = 0
    for user in data_iterator:
        for k, v in user.iteritems():
            if type(v) in [int, float]:
                assert v >= 0, "%s is negative" % (k,)
        dw.writerow(user)

        count += 1
        if not count % 5000:
            logging.info(count)

if __name__ == "__main__":
    main()
