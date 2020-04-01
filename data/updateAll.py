#!/usr/bin/python3

"""Retrieve data from a Routing WS (or Arclink server) to be used locally

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2019 Javier Quinteros, Deutsches GFZ Potsdam <javier@gfz-potsdam.de>
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
from urllib.parse import urlparse

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

sys.path.append('..')

try:
    from routeutils.utils import addRemote
    from routeutils.utils import addRoutes
    from routeutils.utils import addVirtualNets
    from routeutils.utils import cacheStations
    from routeutils.utils import Route
    from routeutils.utils import RoutingCache
except:
    raise


def mergeRoutes(fileRoutes, synchroList, allowOverlaps=False):
    """Retrieve routes from different sources and merge them with the local
ones in the routing tables. The configuration file is checked to see whether
overlapping routes are allowed or not. A pickled version of the the routing
table is saved under the same filename plus ``.bin`` (e.g. routing.xml.bin).

:param fileRoutes: File containing the local routing table
:type fileRoutes: str
:param synchroList: List of data centres where routes should be imported from
:type synchroList: str
:param allowOverlaps: Specify if overlapping streams should be allowed or not
:type allowOverlaps: boolean

"""

    logs = logging.getLogger('mergeRoutes')
    logs.info('Synchronizing with: %s' % synchroList)

    ptRT = addRoutes(fileRoutes, allowOverlaps=allowOverlaps)
    ptVN = addVirtualNets(fileRoutes)

    for line in synchroList.splitlines():
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
                addRemote('./routing-%s.xml' % dcid.strip(), url.strip())
            except:
                msg = 'Failure updating routing information from %s (%s)' % \
                      (dcid, url)
                logs.error(msg)

        if os.path.exists('./routing-%s.xml' % dcid.strip()):
            # FIXME addRoutes should return no Exception ever and skip a
            # problematic file returning a coherent version of the routes
            print('Adding REMOTE %s' % dcid)
            ptRT = addRoutes('./routing-%s.xml' % dcid.strip(),
                             routingTable=ptRT, allowOverlaps=allowOverlaps)
            ptVN = addVirtualNets('./routing-%s.xml' % dcid.strip(),
                                  vnTable=ptVN)

    try:
        os.remove('./%s.bin' % fileRoutes)
    except:
        pass

    stationTable = dict()
    cacheStations(ptRT, stationTable)

    with open('./%s.bin' % fileRoutes, 'wb') as finalRoutes:
        pickle.dump((ptRT, stationTable, ptVN), finalRoutes)
        logs.info('Routes in main Routing Table: %s\n' % len(ptRT))
        logs.info('Stations cached: %s\n' %
                  sum([len(stationTable[dc][st]) for dc in stationTable
                       for st in stationTable[dc]]))
        logs.info('Virtual Networks defined: %s\n' % len(ptVN))


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
    except:
        # If no command-line parameter then read from config file
        try:
            verbo = config.get('Service', 'verbosity')
            verbo = getattr(logging, verbo)
        except:
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
    except:
        pass

    try:
        if 'synchronize' in config.options('Service'):
            synchroList = config.get('Service', 'synchronize')
    except:
        # Otherwise, default value
        synchroList = ''

    mergeRoutes('routing.xml', synchroList)


if __name__ == '__main__':
    main()
