#!/usr/bin/python3

"""Retrieve data from a Routing WS (or Arclink server) to be used locally

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2023 Helmholtz Centre Potsdam GFZ German Research Centre for Geosciences, Potsdam, Germany
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

import os
import sys
import argparse
import logging
import configparser
import pickle
import json
from pprint import pprint
from urllib.parse import urlparse

sys.path.append('..')

try:
    from routeutils.utils import addremote
    from routeutils.utils import addroutes
    from routeutils.utils import addvirtualnets
    from routeutils.utils import cachestations
    from routeutils.utils import Route
    from routeutils.utils import RoutingCache
    from routeutils.utils import replacelast
except Exception:
    raise


def mergeRoutes(fileroutes: str, synchrolist: str, allowOverlaps: bool = False):
    """Retrieve routes from different sources and merge them with the local
ones in the routing tables. The configuration file is checked to see whether
overlapping routes are allowed or not. A pickled version of the the routing
table is saved under the same filename plus ``.bin`` (e.g. routing.xml.bin).

:param fileroutes: File containing the local routing table. Based on this name the JSON file containing the data centre information is derived.
:type fileroutes: str
:param synchrolist: List of data centres where routes should be imported from
:type synchrolist: str
:param allowOverlaps: Specify if overlapping streams should be allowed or not
:type allowOverlaps: bool

"""

    logs = logging.getLogger('mergeRoutes')
    logs.info('Synchronizing with: %s' % synchrolist)

    ptRT = addroutes(fileroutes, allowOverlaps=allowOverlaps)
    ptVN = addvirtualnets(fileroutes)
    eidaDCs = list()
    eidaDCs.append(json.load(open(replacelast(fileroutes, '.xml', '.json'))))

    for line in synchrolist.splitlines():
        if not len(line):
            break
        logs.debug(str(line.split(',')))
        dcid, url = line.split(',')
        url = url.strip()
        parts = urlparse(url)

        if parts.scheme in ('file', ''):
            if parts.path != 'routing-%s.xml' % dcid:
                msg = 'Routes from %s must be in a file called "routing-%s.xml' \
                      % (dcid, dcid)
                logs.error(msg)
                raise Exception('File must be called "routing-%s.xml"' % dcid)
        else:
            try:
                addremote('./routing-%s.xml' % dcid.strip(), url.strip())
                addremote('./routing-%s.json' % dcid.strip(), url.strip(), method='dc')
            except Exception:
                msg = 'Failure updating routing information from %s (%s)' % \
                      (dcid, url)
                logs.error(msg)

        if os.path.exists('./routing-%s.xml' % dcid.strip()):
            # FIXME addroutes should return no Exception ever and skip a
            # problematic file returning a coherent version of the routes
            print('Adding REMOTE %s' % dcid)
            ptRT = addroutes('./routing-%s.xml' % dcid.strip(),
                             routingtable=ptRT, allowOverlaps=allowOverlaps)
            ptVN = addvirtualnets('./routing-%s.xml' % dcid.strip(),
                                  vnTable=ptVN)

        if os.path.exists('./routing-%s.json' % dcid.strip()):
            print('Adding REMOTE data center information from %s' % dcid)
            eidaDCs.append(json.load(open('./routing-%s.json' % dcid.strip())))

    try:
        os.remove('./%s.bin' % fileroutes)
    except Exception:
        pass

    stationTable = dict()
    cachestations(ptRT, stationTable)

    # If in DEBUG logging level
    if logs.getEffectiveLevel() <= logging.DEBUG:
        pprint(ptRT)
        pprint(ptVN)
        pprint(eidaDCs)

    with open('./%s.bin' % fileroutes, 'wb') as finalRoutes:
        pickle.dump((ptRT, stationTable, ptVN, eidaDCs), finalRoutes)
        logs.info('Routes in main Routing Table: %s\n' % len(ptRT))
        logs.info('Stations cached: %s\n' %
                  sum([len(stationTable[dc][st]) for dc in stationTable
                       for st in stationTable[dc]]))
        logs.info('Virtual Networks defined: %s\n' % len(ptVN))
        logs.info('Information from data centers: %s\n' % len(eidaDCs))


def main():
    # FIXME logLevel must be used via argparser
    # Check verbosity in the output
    msg = 'Get EIDA routing configuration and export it to the FDSN-WS style.'
    parser = argparse.ArgumentParser(description=msg)
    parser.add_argument('-l', '--loglevel',
                        help='Verbosity in the output.',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO',
                                 'DEBUG'])
    # TODO Add type=argparse.FileType
    parser.add_argument('-c', '--config',
                        help='Config file to use.',
                        default='../routing.cfg')
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    # Command line parameter has priority
    try:
        verbo = getattr(logging, args.loglevel)
    except Exception:
        # If no command-line parameter then read from config file
        try:
            verbo = config.get('Service', 'verbosity')
            verbo = getattr(logging, verbo)
        except Exception:
            # Otherwise, default value
            verbo = logging.INFO

    # INFO is the default value
    logging.basicConfig(level=verbo)
    logs = logging.getLogger('getEIDAconfig')
    logs.setLevel(verbo)

    if not len(config.read(args.config)):
        logs.error('Configuration file %s could not be read' % args.config)

    print('Skipping routing information. Config file does not allow to '
          + 'overwrite the information. (%s)' % args.config)

    try:
        os.remove('routing-tmp.xml.bin')
    except Exception:
        pass

    # Otherwise, default value
    synchroList = ''
    try:
        if 'synchronize' in config.options('Service'):
            synchroList = config.get('Service', 'synchronize')
    except Exception:
        pass

    mergeRoutes('routing.xml', synchroList)


if __name__ == '__main__':
    main()
