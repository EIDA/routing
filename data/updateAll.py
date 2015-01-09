#!/usr/bin/python

import os
import sys
import ConfigParser
import telnetlib
import cPickle as pickle
from time import sleep

sys.path.append('..')

from utils import addRemote
from utils import addRoutes
from wsgicomm import Logs


def getArcRoutes(arcServ='eida.gfz-potsdam.de', arcPort=18001):
    """Connects via telnet to an Arclink server to get routing information.
The data is saved in the file ``routing.xml``. Generally used to start
operating with an EIDA default configuration.

:param arcServ: Arclink server address
:type arcServ: str
:param arcPort: Arclink server port
:type arcPort: int

.. warning::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = Logs(4)

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
        os.remove(os.path.join(here, 'routing.xml.download'))
    except:
        pass

    with open(os.path.join(here, 'routing.xml.download'), 'w') as fout:
        fout.write(routTable[routTable.find('<'):-3])

    try:
        os.rename(os.path.join(here, './routing.xml'),
                  os.path.join(here, './routing.xml.bck'))
    except:
        pass

    try:
        os.rename(os.path.join(here, './routing.xml.download'),
                  os.path.join(here, './routing.xml'))
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

.. warning::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = Logs(4)

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


def mergeRoutes(synchroList, logs=Logs(2)):
    """Retrieve routes from different sources and merge them witht he local
ones in the three usual routing tables (main, seedlink, station). The
configuration file is checked to see whether overlapping routes are allowed
or not. A pickled version of the three routing tables is saved in
``routing.bin``.

:param synchroList: List of data centres where routes should be imported from
:type synchroList: str
:param logs: Logging object supporting the methods :func:`~Logs.error`,
    :func:`~Logs.warning` and so on.
:type logs: :class:`~Logs`

"""

    ptRT, ptSL, ptST = addRoutes('./routing.xml')

    for line in synchroList.splitlines():
        if not len(line):
            break
        logs.debug(str(line.split(',')))
        dcid, url = line.split(',')
        try:
            addRemote('./' + dcid.strip() + '.xml', url.strip(), logs)
        except:
            msg = 'Failure updating routing information from %s (%s)' % \
                (dcid, url)
            logs.error(msg)

        if os.path.exists('./' + dcid.strip() + '.xml'):
            # FIXME addRoutes should return no Exception ever and skip a
            # problematic file returning a coherent version of the routes
            ptRT, ptSL, ptST = addRoutes('./' + dcid.strip() + '.xml', ptRT,
                                         ptSL, ptST, logs)

    try:
        os.remove('./routing.bin')
    except:
        pass

    with open('./routing.bin', 'wb') as finalRoutes:
        pickle.dump((ptRT, ptSL, ptST), finalRoutes)
        logs.info('Routes in main Routing Table: %s\n' % len(ptRT))
        logs.info('Routes in Station Routing Table: %s\n' % len(ptST))
        logs.info('Routes in Seedlink Routing Table: %s\n' % len(ptSL))

def main(logLevel=2):
    logs = Logs(logLevel)

    # Check Arclink server that must be contacted to get a routing table
    config = ConfigParser.RawConfigParser()

    here = os.path.dirname(__file__)
    config.read(os.path.join(here, '../routing.cfg'))
    arcServ = config.get('Arclink', 'server')
    arcPort = config.getint('Arclink', 'port')

    if config.getboolean('Service', 'ArclinkBased'):
        getArcRoutes(arcServ, arcPort)
    else:
        print 'Skipping routing information. Config file does not allow to ' \
            + 'overwrite the information. (../routing.cfg)'

    synchroList = ''
    if 'synchronize' in config.options('Service'):
        synchroList = config.get('Service', 'synchronize')

    mergeRoutes(synchroList, logs)

    getArcInv(arcServ, arcPort)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(int(sys.argv[1]))
    else:
        main()
