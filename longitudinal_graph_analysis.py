#!/usr/bin/env python

## SYSTEM
import os
import sys
from datetime import datetime as dt, timedelta as td
import logging

## PROJECT
from sonet.timr import Timr
from sonet import mediawiki as mwlib, graph as sg, lib

def create_option_parser():
    import argparse
    from sonet.lib import SonetOption
    
    op = argparse.ArgumentParser(description='Process a graph file running a longitudinal analysis over it.')

    op.add_argument('-S', '--start', action="store", dest='start',
                          type=lib.yyyymmdd_to_datetime, default=None, metavar="YYYYMMDD",
                          help="Look for revisions starting from this date")
    op.add_argument('-E', '--end', action="store", dest='end',
                          type=lib.yyyymmdd_to_datetime, default=None, metavar="YYYYMMDD",
                          help="Look for revisions until this date")
    op.add_argument('-t', '--time-window', help='length for each time window (default: %(default)s)', type=int, default=7)
    op.add_argument('-f', '--freq', help='start date')
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
        
if __name__ == '__main__':
    main()