#!/usr/bin/python

import os
import sys
import telnetlib
import argparse
from time import sleep
import xml.etree.cElementTree as ET

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

sys.path.append('..')

from utils import addRemote
from utils import addRoutes
from utils import Route
from utils import RoutingCache
import logging


def mapArcFDSN(route):
    """Map from an Arclink address to a Dataselect one

:param route: Arclink route
:type route: str
:returns: Base URL equivalent of the given Arclink route
:rtype: str
:raises: Exception

    """

    gfz = 'http://geofon.gfz-potsdam.de'
    odc = 'http://www.orfeus-eu.org'
    eth = 'http://eida.ethz.ch'
    resif = 'http://ws.resif.fr'
    ingv = 'http://webservices.rm.ingv.it'
    bgr = 'http://eida.bgr.de'
    lmu = 'http://erde.geophysik.uni-muenchen.de'
    ipgp = 'http://eida.ipgp.fr'
    niep = 'http://eida-sc3.infp.ro'
    koeri = 'http://eida-service.koeri.boun.edu.tr'

    # Try to identify the hosting institution
    host = route.split(':')[0]

    if host.endswith('gfz-potsdam.de'):
        return gfz
    elif host.endswith('knmi.nl'):
        return odc
    elif host.endswith('ethz.ch'):
        return eth
    elif host.endswith('resif.fr'):
        return resif
    elif host.endswith('ingv.it'):
        return ingv
    elif host.endswith('bgr.de'):
        return bgr
    elif host.startswith('141.84.') or host.endswith('uni-muenchen.de'):
        return lmu
    elif host.endswith('ipgp.fr'):
        return ipgp
    elif host.endswith('infp.ro'):
        return niep
    elif host.endswith('boun.edu.tr') or host.startswith('193.140.203'):
        return koeri
    raise Exception('No FDSN-WS equivalent found for %s' % route)

def arc2fdsnws(filein, fileout, config='../routing.cfg'):
    """Read the routing file in XML format and add the Dataselect and Station
routes based on the Arclink information. The resulting table is stored in the
file passed in the second parameter.

:param filein: Input file with routes (usually from an Arclink server).
:type filein: str
:param fileout: Output file with all routes from the input file plus new
                Station and Dataselect routes based on the Arclink route.
:type fileout: str
"""
    rc = RoutingCache(filein, config=config)
    rOut = RoutingCache()
    for st, lr in rc.routingTable.iteritems():
        toAdd = list()
        for r in lr:
            if r.service == 'arclink':
                stat = Route('station', '%s/fdsnws/station/1/query' %
                             mapArcFDSN(r.address), r.tw, r.priority)
                toAdd.append(stat)

                data = Route('dataselect', '%s/fdsnws/dataselect/1/query' %
                             mapArcFDSN(r.address), r.tw, r.priority)
                toAdd.append(data)

        try:
            rOut.routingTable[st].extend(toAdd)
        except:
            rOut.routingTable[st] = toAdd

    rOut.toXML(fileout)


def getArcRoutes(arcServ='eida.gfz-potsdam.de', arcPort=18002, foutput='routing.xml'):
    """Connects via telnet to an Arclink server to get routing information.
The data is saved in the file specified by foutput. Generally used to start
operating with an EIDA default configuration.

:param arcServ: Arclink server address
:type arcServ: str
:param arcPort: Arclink server port
:type arcPort: int
:param foutput: Filename where the output must be saved
:type foutput: str

.. warning::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = logging.getLogger('getArcRoutes')

    tn = telnetlib.Telnet(arcServ, arcPort)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logs.info(tn.read_until('GFZ', 5))
    tn.write('user routing@eida\n')
    logs.debug(tn.read_until('OK', 5))
    tn.write('request routing\n')
    logs.debug(tn.read_until('OK', 5))
    tn.write('1920,1,1,0,0,0 2030,1,1,0,0,0 * * * *\nEND\n')

    reqID = 0
    while not reqID:
        text = tn.read_until('\n', 5).splitlines()
        for line in text:
            try:
                testReqID = int(line)
            except:
                continue
            if testReqID:
                reqID = testReqID

    myStatus = 'UNSET'
    logs.debug('\n' + myStatus)
    while (myStatus in ('UNSET', 'PROCESSING')):
        sleep(1)
        tn.write('status %s\n' % reqID)
        stText = tn.read_until('END', 15)

        stStr = 'status='
        oldStatus = myStatus
        myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
        myStatus = myStatus.replace('"', '').replace("'", "")
        if myStatus == oldStatus:
            logs.debug('.')
        else:
            logs.debug('\n' + myStatus)

    if myStatus != 'OK':
        logs.error('Error! Request status is not OK.\n')
        return

    tn.write('download %s\n' % reqID)
    routTable = tn.read_until('END', 180)
    start = routTable.find('<')
    logs.info('\nLength: %s\n' % routTable[:start])

    here = os.path.dirname(__file__)
    try:
        os.remove(os.path.join(here, '%s.download' % foutput))
    except:
        pass

    with open(os.path.join(here, '%s.download' % foutput), 'w') as fout:
        fout.write(routTable[routTable.find('<'):-3])

    try:
        os.rename(os.path.join(here, foutput),
                  os.path.join(here, '%s.bck' % foutput))
    except:
        pass

    try:
        os.rename(os.path.join(here, '%s.download' % foutput),
                  os.path.join(here, foutput))
    except:
        pass

    logs.info('Routing information succesfully read from Arclink!\n')


def getArcInv(arcServ='eida.gfz-potsdam.de', arcPort=18001):
    """Connects via telnet to an Arclink server to get inventory information.
The data is saved in the file ``Arclink-inventory.xml``. Generally used to
start operating with an EIDA default configuration.

:param arcServ: Arclink server address
:type arcServ: str
:param arcPort: Arclink server port
:type arcPort: int

.. deprecated:: since version 1.0.2

.. warning::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = logging.getLogger('getArcInv')

    logs.warning('This function should probably not be used! Be carefull!')

    tn = telnetlib.Telnet(arcServ, arcPort)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logs.info(tn.read_until('GFZ', 5))
    tn.write('user routing@eida\n')
    logs.debug('\nuser routing@eida')
    logs.debug(tn.read_until('OK', 5))
    tn.write('request inventory\n')
    logs.debug('\nrequest inventory')
    logs.debug(tn.read_until('OK', 5))
    tn.write('1920,1,1,0,0,0 2030,1,1,0,0,0 * * * *\nEND\n')
    logs.debug('\n1920,1,1,0,0,0 2030,1,1,0,0,0 * * * *\nEND')

    reqID = 0
    while not reqID:
        text = tn.read_until('\n', 5).splitlines()
        for line in text:
            try:
                testReqID = int(line)
            except:
                continue
            if testReqID:
                reqID = testReqID

    logs.debug('status %s\n' % reqID)
    myStatus = 'UNSET'
    logs.debug('\n' + myStatus)
    while (myStatus in ('UNSET', 'PROCESSING')):
        sleep(1)
        tn.write('status %s\n' % reqID)
        stText = tn.read_until('END', 15)

        stStr = 'status='
        oldStatus = myStatus
        myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
        myStatus = myStatus.replace('"', '').replace("'", "")
        if myStatus == oldStatus:
            logs.debug('.')
        else:
            logs.debug('\n' + myStatus)

    if myStatus != 'OK':
        logs.error('Error! Request status is not OK.\n')
        return

    tn.write('download %s\n' % reqID)
    logs.debug('download %s\n' % reqID)
    here = os.path.dirname(__file__)
    try:
        os.remove(os.path.join(here, 'Arclink-inventory.xml.download'))
    except:
        pass

    # Write the downloaded file

    with open(os.path.join(here, 'Arclink-inventory.xml.download'), 'w') \
            as fout:
        #try:
        fd = tn.get_socket().makefile('rb+')
        # Read the size of the inventory
        length = fd.readline(100).strip()
        # Max number of retries
        maxRet = 8
        while not isinstance(length, int) and maxRet:
            try:
                length = int(length)
            except:
                sleep(1)
                tn.write('download %s\n' % reqID)
                logs.debug('Retrying! download %s\n' % reqID)
                length = fd.readline(100).strip()
                maxRet -= 1

        logs.info('\nExpected size: %s\n' % length)
        bytesRead = 0
        while bytesRead < length:
            buf = fd.read(min(4096, length - bytesRead))
            bytesRead += len(buf)
            bar = '|' + '=' * int(bytesRead * 100 / (2 * length)) + \
                ' ' * int((length - bytesRead) * 100 / (2 * length)) + '|'
            logs.debug('\r%s' % bar)
            fout.write(buf)

        buf = fd.readline(100).strip()
        if buf != "END" or bytesRead != length:
            raise Exception('Wrong length!')
        #finally:
        #    tn.write('PURGE %d\n' % reqID)

    try:
        os.rename(os.path.join(here, './Arclink-inventory.xml'),
                  os.path.join(here, './Arclink-inventory.xml.bck'))
    except:
        pass

    try:
        os.rename(os.path.join(here, './Arclink-inventory.xml.download'),
                  os.path.join(here, './Arclink-inventory.xml'))
    except:
        pass

    logs.info('\nInventory read from Arclink!\n')


def mergeRoutes(fileRoutes, synchroList, allowOverlaps=False):
    """Retrieve routes from different sources and merge them with the local
ones in the routing tables. The configuration file is checked to see whether
overlapping routes are allowed or not. A pickled version of the the routing
table is saved under the same filename plus ``.bin`` (e.g. routing.xml.bin).

:param fileRoutes: File containing the local routing table
:type fileRoutes: str
:param synchroList: List of data centres where routes should be imported from
:type synchroList: str
:param allowOverlaps: Specify if overlapping streams should be allowed or discarded
:type allowOverlaps: boolean

"""

    logs = logging.getLogger('mergeRoutes')
    logs.info('Synchronizing with: %s' % synchroList)

    ptRT = addRoutes(fileRoutes, allowOverlaps=allowOverlaps)

    for line in synchroList.splitlines():
        if not len(line):
            break
        logs.debug(str(line.split(',')))
        dcid, url = line.split(',')
        try:
            addRemote('./routing-%s.xml' % dcid.strip(), url.strip())
        except:
            msg = 'Failure updating routing information from %s (%s)' % \
                (dcid, url)
            logs.error(msg)

        if os.path.exists('./routing-%s.xml' % dcid.strip()):
            # FIXME addRoutes should return no Exception ever and skip a
            # problematic file returning a coherent version of the routes
            print 'Adding REMOTE %s' % dcid
            ptRT = addRoutes('./routing-%s.xml' % dcid.strip(),
                             routingTable=ptRT, allowOverlaps=allowOverlaps)

    try:
        os.remove('./%s.bin' % fileRoutes)
    except:
        pass

    with open('./%s.bin' % fileRoutes, 'wb') as finalRoutes:
        pickle.dump(ptRT, finalRoutes)
        logs.info('Routes in main Routing Table: %s\n' % len(ptRT))


def main():
    # FIXME logLevel must be used via argparser
    # Check verbosity in the output
    parser = argparse.ArgumentParser(description='Get EIDA routing configuration and "export" it to the FDSN-WS style.')
    parser.add_argument('-l', '--loglevel',
                        help='Verbosity in the output.',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'])
    parser.add_argument('-s', '--server',
            help='Arclink server address (address.domain:18001).')
    parser.add_argument('-c', '--config',
                        help='Config file to use.',
                        default='../routing.cfg')
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    if not len(config.read(args.config)):
        logs.error('Configuration file %s could not be read' % args.config)
        return

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

    # Check Arclink server that must be contacted to get a routing table
    if args.server:
        arcServ, arcPort = args.server.split(':')
    else:
        # If no command-line parameter then read from config file
        try:
            arcServ = config.get('Arclink', 'server')
            arcPort = config.getint('Arclink', 'port')
        except:
            # Otherwise, default value
            arcServ = 'eida.gfz-potsdam.de'
            arcPort = 18002


    if config.getboolean('Service', 'ArclinkBased'):
        logs.info('Starting routing table creation based on Arclink data')
        getArcRoutes(arcServ, arcPort, 'routing-tmp.xml')
        logs.info('Adding Station and Dataselect routes based on Arclink data')
        arc2fdsnws('routing-tmp.xml', 'routing.xml', config=args.config)
        try:
            os.remove('routing-tmp.xml')
            logs.debug('routing-tmp.xml removed')
        except:
            pass

    else:
        print 'Skipping routing information. Config file does not allow to ' \
            + 'overwrite the information. (%s)' % args.config

    try:
        os.remove('routing-tmp.xml.bin')
    except:
        pass

    synchroList = ''
    if 'synchronize' in config.options('Service'):
        synchroList = config.get('Service', 'synchronize')

    mergeRoutes('routing.xml', synchroList)


if __name__ == '__main__':
    main()
