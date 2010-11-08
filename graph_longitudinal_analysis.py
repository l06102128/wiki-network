#!/usr/bin/env python

## SYSTEM
import os, sys
import gc
import logging

from datetime import datetime as dt, timedelta
from copy import deepcopy
from math import ceil

## PROJECT LIBS
from sonet.timr import Timr
from sonet import mediawiki as mwlib, graph as sg, lib

def process_graph(graph, start, end):
    df = "%Y-%m-%d %H:%M"
    ## create a sub-graph on time boundaries
    logging.info("SINCE %s TO %s" % (
        start.strftime(df), end.strftime(df))
    )
    graph.time_slice_subgraph(start=start, end=end)
    print_graph_stat(graph.g)
    del graph
    
def print_graph_stat(g):
    print g.summary()
    print
    del g

def create_option_parser():
    import argparse
    from sonet.lib import SonetOption
    
    p = argparse.ArgumentParser(description='Process a graph file running a longitudinal analysis over it.')

    p.add_argument('-s', '--start', type=lib.yyyymmdd_to_datetime, metavar="YYYYMMDD",
                          help="Look for revisions starting from this date", default="20010101")
    p.add_argument('-e', '--end', action="store", dest='end',
                          type=lib.yyyymmdd_to_datetime, default=None, metavar="YYYYMMDD",
                          help="Look for revisions until this date")
    p.add_argument('-t', '--time-window', help='length for each time window (default: %(default)s)', type=int, default=7)
    p.add_argument('-f', '--frequency', help='time window frequency', type=int, default=0)
    p.add_argument('-c', '--cumulative', help='cumulative graph analysis, fixed start date', action='store_true')
    p.add_argument('file_name', help="file containing the graph to be analyzed")
    
    return p

def main():

    logging.basicConfig(#filename="graph_longiudinal_analysis.log",
                                stream=sys.stderr,
                                level=logging.DEBUG)
    logging.info('---------------------START---------------------')
    
    op = create_option_parser()

    args = op.parse_args()
    


    ## explode dump filename in order to obtain wiki lang, dump date and type
    lang, date_, type_ = mwlib.explode_dump_filename(args.file_name)
                    
    start, tw = args.start, args.time_window
    ## if end argument is not specified, then use the dump date
    end = args.end if args.end else lib.yyyymmdd_to_datetime(date_)
    ## frequency not to be considered in case of cumulative analysis
    freq = args.frequency if (args.frequency and not args.cumulative) else tw

    freq_range = int( ceil( ( (end - start).days + 1) / float(freq) ) )

    with Timr("LONGITUDINAL ANALYSIS"):
        ## date range used for sub-graph analysis
        for d in [start + timedelta(freq * d) for d in range(freq_range)]:
            ## if analysing in a cumulative way, keep start date fixed
            s = start if args.cumulative else d
            e = d + timedelta(tw) if (d + timedelta(tw) <= end) else end + timedelta(1)

            ## graph loading
            try:
                g = sg.load(args.file_name)
            except IOError:
                print "unable to load a graph from passed file:", args.file_name
                return
            
            process_graph(graph=g, start=s, end=e)
            del g
            gc.collect()
        
        
if __name__ == '__main__':
    #import cProfile as profile
    #profile.run('main()', 'mainprof')
    main()
    ## NOT WORKING WITH PYTHON2.7
    #h = guppy.hpy()
    #print h.heap()