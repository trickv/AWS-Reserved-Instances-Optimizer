#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# @Author: "Charlie Schluting <charlie@schluting.com>"
# @Date:   June 2012
#
# Script to analyze reserved instance utilization.
#
# Identifies:
#   - reservations that aren't being used
#   - running instances that aren't reserved
#   - cost savings if you were to reserve all running on-demand instances
#
# TODO: how to handle light/medium utilization instances? This script assumes /
# only cares about heavy-utilization 1-year reserved instances.
#
# TODO: I'm formatting currency based on locale, but doesn't AWS always
# charge in $USD?
#
# Requires: ~/.boto, boto lib, texttable lib
#
#
import sys
import os
import re
import math
import logging
import boto.ec2
import locale
import texttable
from optparse import OptionParser

locale.setlocale(locale.LC_ALL, '')

parser = OptionParser("usage: %prog [options]")
parser.add_option("-d", "--debug", default=None, action="store_true",
                  help="enable debug output")
parser.add_option("-l", "--list", default=None, action="store_true",
                  help="list all reservations and exit")
parser.add_option("-e", "--exclude", metavar="regex", default='__None__',
                  help="exclude instances by security group name. takes regex")
parser.add_option("-r", "--region", default='us-east-1',
                  help="ec2 region to connect to")
parser.add_option("--vpc", default=False, action="store_true",
                  help="operate on VPC instances/reservations only")
(options, args) = parser.parse_args()

# set up logging
if options.debug:
    log_level = logging.DEBUG
else:
    log_level = logging.INFO

logging.basicConfig(stream=sys.stdout, level=log_level)
logging.basicConfig(stream=sys.stderr, level=(logging.ERROR, logging.CRITICAL))

def summarize_tuples(items):
    ''' takes a tuple of properties, and summarizes into a dict.
        input: (instance_type, availability_zone, instance_count) '''
    result = {}
    for res in items:
        key = (res[0], res[1])
        if key not in result:
            result.update({key: res[2]})
        else:
            result[key] += res[2]
    return result

if __name__ == '__main__':
    # TODO: security group based filtering doesn't work on VPC instances.
    if "None" not in options.exclude and options.vpc:
        logging.error("Sorry, you can't currently exclude by security group "
                      "regex with VPC enabled.")
        sys.exit(1)

        sys.exit(0)

    conn = boto.ec2.connect_to_region(options.region)

    # not filtering by security group? it'll break with vpc instances that
    # don't have a 'name' attribute, so don't even try:
    if "None" not in options.exclude:
        instances = [i for r in conn.get_all_instances()
                     for i in r.instances
                     if len(r.groups) > 0 and not re.match(options.exclude, r.groups[0].name)]
    else:
        instances = [i for r in conn.get_all_instances() for i in r.instances]

    active_reservations = [i for i in conn.get_all_reserved_instances()
                           if 'active' in i.state
                           or 'payment-pending' in i.state]

    # re-set list of instances and reservations to only VPC ones, if --vpc
    # otherwise, exclude VPC instances/reservations. *hacky*
    if options.vpc:
        active_reservations = [res for res in active_reservations
                               if "VPC" in res.description]
        instances = [inst for inst in instances if inst.vpc_id]
    else:
        active_reservations = [res for res in active_reservations
                               if "VPC" not in res.description]
        instances = [inst for inst in instances if inst.vpc_id is None]

    # no instances were found, just bail:
    if len(instances) == 0:
        logging.error("Sorry, you don't seem to have any instances "
                      "here. Nothing to do. (try --vpc?)")
        sys.exit(1)

    all_res = [(res.instance_type + '-' + ('windows' if res.description.startswith('Windows') else 'linux'),
                res.availability_zone,
                res.instance_count) for res in active_reservations]
    res_dict = summarize_tuples(all_res)

    ''' just print reservations, if -l is used '''
    if options.list:
        print "Current active reservations:\n"
        for i in sorted(res_dict.iteritems()):
            print i[0][0], i[0][1], i[1]
        sys.exit(0)

    ''' find cases where we're running fewer instances than we've reserved '''
    for res in active_reservations:
        matches = [
            i for i in instances if res.availability_zone in i.placement]
        running = len(
            [i.instance_type for i in matches
                if i.instance_type in res.instance_type
                and "running" in i.state])

        if running < res.instance_count:

            print "ERR: only %i running %s instances in %s, but %s are " \
                  "reserved!" % (running, res.instance_type,
                          res.availability_zone, res.instance_count)

    ''' identify non-reserved running instances '''

    all_instances = [(ins.instance_type + '-' + (ins.platform if ins.platform is not None else 'linux'),
                     ins.placement, 1)
                     for ins in instances if "running" in ins.state]
    ins_dict = summarize_tuples(all_instances).iteritems()

    print "\n== Summary of running instances and their reserved instances ==\n"

    total_instances = 0
    res_instances = 0

    table = texttable.Texttable(max_width=0)
    table.set_deco(texttable.Texttable.HEADER)
    table.set_cols_dtype(['t', 't', 't', 't'])
    table.set_cols_align(["l", "c", "c", "c"])
    table.add_row(
        ["instance type", "zone", "# running", "# reserved"])

    for i in sorted(ins_dict):
        # dict i is: {(inst_type, az): count}

        # find # of reserved instances, and # on-demand:
        if i[0] in res_dict:
            res_count = int(res_dict[i[0]])
        else:
            res_count = 0

        run_count = int(i[1])

        inst_type, az = i[0]

        total_instances += int(run_count)
        res_instances += int(res_count)

        table.add_row(
            [inst_type, az, run_count, res_count,
             ])

    table.add_row(['---', '', '', ''])
    table.add_row(['Totals:', '', total_instances, res_instances,
         ])
    print table.draw()
