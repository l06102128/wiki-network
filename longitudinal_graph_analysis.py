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
    print start, end
    graph.time_slice_subgraph(start=start, end=end)
    print_graph_stat(graph.g)
    del graph
    
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
        
    lang, date_, type_ = mwlib.explode_dump_filename(args.file_name)
    
    ## if end argument is not specified, then use the date
    ## of the dump
    if not args.end:
        args.end = lib.yyyymmdd_to_datetime(date_)
                
    start, end, tw = args.start, args.end, args.time_window
    cumulative = args.cumulative
    freq = args.frequency if args.frequency and not cumulative else tw
            
    freq_range = int( ceil( ( (end - start).days + 1) / float(freq) ) )
    
    for d in [start + timedelta(freq * d) for d in range(freq_range)]:
        s = start if cumulative else d
        process_graph(graph=deepcopy(g), start=s, end=d + timedelta(tw))
        
if __name__ == '__main__':
    main()