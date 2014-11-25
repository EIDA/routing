#!/usr/bin/python

import os
import sys
import ConfigParser
import telnetlib
from time import sleep


class Logs(object):
    """
:synopsis: Given the log level redirects the output to the proper destination
:platform: Linux

"""

    def __init__(self, level=2):
        self.setLevel(level)

    def setLevel(self, level):
        """Set the level of the log

:param level: Log level (1: Error, 2: Warning, 3: Info, 4: Debug)
:type level: int

        """

        # Remap the functions in agreement with the output level
        # Default values are the following
        self.error = self.__write
        self.warning = self.__write
        self.info = self.__pass
        self.debug = self.__pass

        if level >= 2:
            self.warning = self.__write
        if level >= 3:
            self.info = self.__write
        if level >= 4:
            self.debug = self.__write

    def __write(self, msg):
        sys.stdout.write(msg)
        sys.stdout.flush()

    def __pass(self, msg):
        pass


def configArclink():
    """Connects via telnet to an Arclink server to get routing information.
The address and port of the server are read from ``routing.cfg``.
The data is saved in the file ``routing.xml``. Generally used to start operating
with an EIDA default configuration.

.. note::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = Logs(4)
    
    # Check Arclink server that must be contacted to get a routing table
    config = ConfigParser.RawConfigParser()

    here = os.path.dirname(__file__)
    config.read(os.path.join(here, '../routing.cfg'))
    arcServ = config.get('Arclink', 'server')
    arcPort = config.getint('Arclink', 'port')

    tn = telnetlib.Telnet(arcServ, arcPort)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logs.info(tn.read_until('GFZ', 5) + '\n')
    tn.write('user routing@eida\n')
    logs.debug(tn.read_until('OK', 5) + '\n')
    tn.write('request routing\n')
    logs.debug(tn.read_until('OK', 5) + '\n')
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
    while (myStatus in ('UNSET', 'PROCESSING')):
        sleep(1)
        tn.write('status %s\n' % reqID)
        stText = tn.read_until('END', 15)

        stStr = 'status='
        myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
        myStatus = myStatus.replace('"', '').replace("'", "")
        logs.debug(myStatus + '\n')

    if myStatus != 'OK':
        logs.error('Error! Request status is not OK.\n')
        return

    tn.write('download %s\n' % reqID)
    routTable = tn.read_until('END', 180)
    start = routTable.find('<')
    logs.info('Length: %s\n' % routTable[:start])

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

    logs.info('Configuration read from Arclink!\n')


def configArclinkInv():
    """Connects via telnet to an Arclink server to get inventory information.
The address and port of the server are read from ``routing.cfg``.
The data is saved in the file ``Arclink-inventory.xml``. Generally used to
start operating with an EIDA default configuration.

.. note::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

    """

    logs = Logs(4)
    
    # Check Arclink server that must be contacted to get a routing table
    config = ConfigParser.RawConfigParser()

    here = os.path.dirname(__file__)
    config.read(os.path.join(here, '../routing.cfg'))
    arcServ = config.get('Arclink', 'server')
    arcPort = config.getint('Arclink', 'port')

    tn = telnetlib.Telnet(arcServ, arcPort)
    tn.write('HELLO\n')
    # FIXME The institution should be detected here. Shouldn't it?
    logs.info(tn.read_until('GFZ', 5))
    tn.write('user routing@eida\n')
    logs.debug(tn.read_until('OK', 5))
    tn.write('request inventory\n')
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
        length = int(fd.readline(100).strip())
        logs.info('\nExpected size: %s\n' % length)
        bytesRead = 0
        while bytesRead < length:
            buf = fd.read(min(4096, length - bytesRead))
            bytesRead += len(buf)
            bar = '|' + '=' * int(bytesRead * 100 / length) + \
                    ' ' * int((length - bytesRead) * 100 / length) + '|'
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


configArclink()
configArclinkInv()

