#!/usr/bin/env python

## SYSTEM
import os
import sys
import logging

from datetime import datetime as dt, timedelta
from copy import deepcopy
from math import ceil

## PROJECT LIBS
from sonet.timr import Timr
from sonet import mediawiki as mwlib, graph as sg, lib

def process_graph(graph, start, end):
    ## create a sub-graph on time boundaries
    graph.time_slice_subgraph(start=start, end=end)
    print_graph_stat(graph.g)
    
def print_graph_stat(g):
    print g.summary()
    print

def create_option_parser():
    import argparse
    from sonet.lib import SonetOption
    
    op = argparse.ArgumentParser(description='Process a graph file running a longitudinal analysis over it.')

    op.add_argument('-s', '--start', type=lib.yyyymmdd_to_datetime, metavar="YYYYMMDD",
                          help="Look for revisions starting from this date", default="20010101")
    op.add_argument('-e', '--end', action="store", dest='end',
                          type=lib.yyyymmdd_to_datetime, default=None, metavar="YYYYMMDD",
                          help="Look for revisions until this date")
    op.add_argument('-t', '--time-window', help='length for each time window (default: %(default)s)', type=int, default=7)
    op.add_argument('-f', '--frequency', help='time window frequency', type=int, default=0)
    op.add_argument('-c', '--cumulative', help='cumulative graph analysis, fixed start date', action='store_true')
    op.add_argument('file_name', help="file containing the graph to be analyzed")
    
    return op

def main():
    op = create_option_parser()

    args = op.parse_args()
    
    try:
        g = sg.load(args.file_name)
    except IOError:
        print "unable to load a graph from passed file:", args.file_name
        return

    ## explode dump filename in order to obtain wiki lang, dump date and type
    lang, date_, type_ = mwlib.explode_dump_filename(args.file_name)
                    
    start, tw = args.start, args.time_window
    ## if end argument is not specified, then use the dump date
    end = args.end if args.end else lib.yyyymmdd_to_datetime(date_)
    ## frequency not to be considered in case of cumulative analysis
    freq = args.frequency if args.frequency and not args.cumulative else tw

    freq_range = int( ceil( ( (end - start).days + 1) / float(freq) ) )

    with Timr("Longitudinal analysis"):
        ## date range used for sub-graph analysis
        for d in [start + timedelta(freq * d) for d in range(freq_range)]:
            ## if analysing in a cumulative way, keep start date fixed
            s = start if args.cumulative else d
            ## deepcopy the graph into memory
            g2 = deepcopy(g)
            process_graph(graph=g2, start=s, end=d + timedelta(tw))
            del g2
        
        
if __name__ == '__main__':
    # import cProfile as profile
    # profile.run('main()', 'mainprof')
    main()
    ## NOT WORKING WITH PYTHON2.7
    # h = guppy.hpy()
    # print h.heap()