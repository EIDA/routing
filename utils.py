#!/usr/bin/env python
#
# Routing WS prototype
#
# (c) 2014 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Classes to be used by the Routing WS for EIDA

   :Platform:
       Linux
   :Copyright:
       GEOFON, GFZ Potsdam <geofon@gfz-potsdam.de>
   :License:
       To be decided!

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

##################################################################
#
# First all the imports
#
##################################################################


import os
import datetime
import fnmatch
import telnetlib
import xml.etree.cElementTree as ET
import urllib2
import cPickle as pickle
import ConfigParser
from time import sleep
from collections import namedtuple
from operator import add
from operator import itemgetter
from inventorycache import InventoryCache
from wsgicomm import Logs


def checkOverlap(str1, routeList, str2, route, logs=Logs(2)):
    if str1.overlap(str2):
        for auxRoute in routeList:
            if auxRoute.overlap(route):
                return True

    return False


def addRoutes(fileName, ptRT=dict(), ptSL=dict(), ptST=dict(), logs=Logs(2)):
    """Read the routing file in XML format and store it in memory.

All the routing information is read into a dictionary. Only the
necessary attributes are stored. This relies on the idea
that some other agent should update the routing file at
a regular period of time.

:param fileName: File with routes to add the the routing table.
:type fileName: str
:returns: Three dictionaries with the routing tables (main, seedlink, station)
:rtype: tuple
"""

    logs.debug('Entering addRoutes(%s)\n' % fileName)

    # Read the configuration file and checks when do we need to update
    # the routes
    config = ConfigParser.RawConfigParser()

    here = os.path.dirname(__file__)
    config.read(os.path.join(here, 'routing.cfg'))

    if 'allowoverlap' in config.options('Service'):
        allowOverlap = config.getboolean('Service', 'allowoverlap')
    else:
        allowOverlap = False

    with open(fileName, 'r') as testFile:
        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            context = ET.iterparse(testFile, events=("start", "end"))
        except IOError:
            msg = 'Error: %s could not be opened. Skipping it!\n' % fileName
            logs.error(msg)
            return (ptRT, ptSL, ptST)

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = context.next()

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = '%s seems not to be a routing file (XML). Skipping it!\n' \
                % fileName
            logs.error(msg)
            return (ptRT, ptSL, ptST)

        # Extract the namespace from the root node
        namesp = root.tag[:-len('routing')]

        for event, route in context:
            # The tag of this node should be "route".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if route.tag == namesp + 'route':

                    # Extract the location code
                    try:
                        locationCode = route.get('locationCode')
                        if len(locationCode) == 0:
                            locationCode = '*'
                    except:
                        locationCode = '*'

                    # Extract the network code
                    try:
                        networkCode = route.get('networkCode')
                        if len(networkCode) == 0:
                            networkCode = '*'
                    except:
                        networkCode = '*'

                    # Extract the station code
                    try:
                        stationCode = route.get('stationCode')
                        if len(stationCode) == 0:
                            stationCode = '*'
                    except:
                        stationCode = '*'

                    # Extract the stream code
                    try:
                        streamCode = route.get('streamCode')
                        if len(streamCode) == 0:
                            streamCode = '*'
                    except:
                        streamCode = '*'

                    # Traverse through the sources
                    for sl in route.findall(namesp + 'seedlink'):
                        # Extract the address
                        try:
                            address = sl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        # Extract the priority
                        try:
                            priority = sl.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)

                        try:
                            # Check the overlap between the routes to import
                            # and the ones already present in the Seedlink
                            # Routing table
                            addIt = True
                            logs.debug('[SL] Checking %s\n' % str(st))
                            for testStr in ptSL.keys():
                                # This checks the overlap of Streams and also
                                # of timewindows and priority
                                if checkOverlap(testStr, ptSL[testStr], st,
                                                Route(address, TW(None, None),
                                                      priority)):
                                    msg = '%s: Overlap between %s and %s!\n'\
                                        % (fileName, st, testStr)
                                    logs.error(msg)
                                    if not allowOverlap:
                                        logs.error('Skipping %s\n' % str(st))
                                        addIt = False
                                    break

                            if addIt:
                                ptSL[st].append(Route(address, TW(None, None),
                                                      priority))
                            else:
                                logs.warning('Skip %s - %s\n' %
                                             (st, Route(address,
                                                        TW(None, None),
                                                        priority)))

                        except KeyError:
                            ptSL[st] = [Route(address, TW(None, None),
                                              priority)]
                        sl.clear()

                    # Traverse through the sources
                    for arcl in route.findall(namesp + 'arclink'):
                        # Extract the address
                        try:
                            address = arcl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        try:
                            startD = arcl.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            msg = 'Error while converting START attribute\n'
                            logs.error(msg)

                        # Extract the end datetime
                        try:
                            endD = arcl.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int,
                                                              endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            msg = 'Error while converting END attribute.\n'
                            logs.error(msg)

                        # Extract the priority
                        try:
                            priority = arcl.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)
                        tw = TW(startD, endD)

                        try:
                            # Check the overlap between the routes to import
                            # and the ones already present in the main Routing
                            # table
                            addIt = True
                            logs.debug('[RT] Checking %s\n' % str(st))
                            for testStr in ptRT.keys():
                                # This checks the overlap of Streams and also
                                # of timewindows and priority
                                if checkOverlap(testStr, ptRT[testStr], st,
                                                Route(address, tw, priority)):
                                    msg = '%s: Overlap between %s and %s!\n'\
                                        % (fileName, st, testStr)
                                    logs.error(msg)
                                    if not allowOverlap:
                                        logs.error('Skipping %s\n' % str(st))
                                        addIt = False
                                    break

                            if addIt:
                                ptRT[st].append(Route(address, tw, priority))
                            else:
                                logs.warning('Skip %s - %s\n' %
                                             (st, Route(address, tw,
                                                        priority)))

                        except KeyError:
                            ptRT[st] = [Route(address, tw, priority)]
                        arcl.clear()

                    # Traverse through the sources
                    for statServ in route.findall(namesp + 'station'):
                        # Extract the address
                        try:
                            address = statServ.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        try:
                            startD = statServ.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            msg = 'Error while converting START attribute\n'
                            logs.error(msg)

                        # Extract the end datetime
                        try:
                            endD = statServ.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int, endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            msg = 'Error while converting END attribute.\n'
                            logs.error(msg)

                        # Extract the priority
                        try:
                            priority = statServ.get('priority')
                            if len(address) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)
                        tw = TW(startD, endD)

                        try:
                            # Check the overlap between the routes to import
                            # and the ones already present in the Station
                            # Routing table
                            addIt = True
                            logs.debug('[ST] Checking %s\n' % str(st))
                            for testStr in ptST.keys():
                                # This checks the overlap of Streams and also
                                # of timewindows and priority
                                if checkOverlap(testStr, ptST[testStr], st,
                                                Route(address, tw, priority)):
                                    msg = '%s: Overlap between %s and %s!\n'\
                                        % (fileName, st, testStr)
                                    logs.error(msg)
                                    if not allowOverlap:
                                        logs.error('Skipping %s\n' % str(st))
                                        addIt = False
                                    break

                            if addIt:
                                ptST[st].append(Route(address, tw, priority))
                            else:
                                logs.warning('Skip %s - %s\n' %
                                             (st, Route(address, tw,
                                                        priority)))

                        except KeyError:
                            ptST[st] = [Route(address, tw, priority)]
                        statServ.clear()

                    route.clear()

                root.clear()

    # Order the routes by priority
    for keyDict in ptRT:
        ptRT[keyDict] = sorted(ptRT[keyDict])

    # Order the routes by priority
    for keyDict in ptSL:
        ptSL[keyDict] = sorted(ptSL[keyDict])

    # Order the routes by priority
    for keyDict in ptST:
        ptST[keyDict] = sorted(ptST[keyDict])

    return (ptRT, ptSL, ptST)


def addRemote(fileName, url, logs=Logs(2)):
    """Read the routing file from a remote datacenter and store it in memory.

    All the routing information is read into a dictionary. Only the
    necessary attributes are stored.

    :param dcid: Datacenter ID
    :type dcid: str
    :param url: Base URL from the Routing Service at the remote datacenter
    :type url: str
    :raise: Exception

    """

    logs.debug('Entering addRemote(%s)\n' %
               os.path.basename(fileName))

    # Prepare Request
    req = urllib2.Request(url + '/localconfig')

    blockSize = 4096

    #here = os.path.dirname(__file__)
    #fileName = os.path.join(here, 'data', dcid + '.xml.download')

    fileName = fileName + '.download'

    try:
        os.remove(fileName)
        logs.debug('Successfully removed %s\n' % fileName)
    except:
        pass

    # Connect to the proper Routing-WS
    try:
        u = urllib2.urlopen(req)

        with open(fileName, 'w') as routeExt:
            logs.debug('%s opened\n%s:' % (fileName, url))
            # Read the data in blocks of predefined size
            buf = u.read(blockSize)
            while len(buf):
                logs.debug('.')
                # Return one block of data
                routeExt.write(buf)
                buf = u.read(blockSize)

            # Close the connection to avoid overloading the server
            u.close()

    except urllib2.URLError as e:
        if hasattr(e, 'reason'):
            logs.error('%s - Reason: %s\n' % (url, e.reason))
        elif hasattr(e, 'code'):
            logs.error('The server couldn\'t fulfill the')
            logs.error(' request.\nError code: %s\n', e.code)

    name = fileName[:- len('.download')]
    try:
        os.remove(name + '.bck')
        logs.debug('Successfully removed %s\n' % (name + '.bck'))
    except:
        pass

    try:
        os.rename(name, name + '.bck')
        logs.debug('Successfully renamed %s to %s.bck\n' % (name, name))
    except:
        pass

    try:
        os.rename(fileName, name)
        logs.debug('Successfully renamed %s to %s\n' % (fileName, name))
    except:
        raise Exception('Could not create the final version of %s.xml' %
                        os.path.basename(fileName))


class RequestMerge(list):
    """
:synopsis: Extend a list to group automatically by datacenter the information
           from many requests
:platform: Any
    """

    __slots__ = ()

    def append(self, service, url, priority, stream, start=None,
               end=None):
        """Append a new :class:`~Route` without repeating the datacenter.

Overrides the *append* method of the inherited list. If another route for the
datacenter was already added, the remaining attributes are appended in
*params* for the datacenter. If this is the first :class:`~Route` for the
datacenter, everything is added.

:param service: Service name (f.i., 'dataselect')
:type service: str
:param url: URL for the service (f.i., 'http://server/path/query')
:type url: str
:param priority: Priority of the Route (1: highest priority)
:type priority: int
:param stream: Stream(s) associated with the Route
:type stream: :class:`~Stream`
:param start: Start date for the Route
:type start: datetime or None
:param end: End date for the Route
:type end: datetime or None
        """

        try:
            pos = self.index(service, url)
            self[pos]['params'].append({'net': stream.n, 'sta': stream.s,
                                        'loc': stream.l, 'cha': stream.c,
                                        'start': start, 'end': end,
                                        'priority': priority if priority
                                        is not None else ''})
        except:
            # Take a reference to the inherited *list* and do a normal append
            listPar = super(RequestMerge, self)
            listPar.append({'name': service, 'url': url,
                            'params': [{'net': stream.n, 'sta': stream.s,
                                        'loc': stream.l, 'cha': stream.c,
                                        'start': start, 'end': end,
                                        'priority': priority if priority
                                        is not None else ''}]})

    def index(self, service, url):
        """Check for the presence of the datacenter and service specified in
the parameters. This overrides the *index* method of the inherited list.

:param service: Requests from (possibly) different datacenters to be added
:type service: str
:param url: Address of the service provided by a datacenter
:type url: str
:returns: position in the list where the service and url specified can
          be found
:rtype: int
:raises: ValueError
        """

        for ind, r in enumerate(self):
            if ((r['name'] == service) and (r['url'] == url)):
                return ind

        raise ValueError()

    def extend(self, listReqM):
        """Append all the items in the list of :class:`~RequestMerge` without
repeating the datacenter.

Overrides the *extend* method of the inherited list. If another route for the
datacenter was already added, the remaining attributes are appended in
*params* for the datacenter. If this is the first :class:`~Route` for the
datacenter, everything is added.

:param listReqM: Requests from (posibly) different datacenters to be added
:type listReqM: list of :class:`~RequestMerge`
        """

        for r in listReqM:
            try:
                pos = self.index(r['name'], r['url'])
                self[pos]['params'].extend(r['params'])
            except:
                super(RequestMerge, self).append(r)


class Stream(namedtuple('Stream', ['n', 's', 'l', 'c'])):
    """
:synopsis: Namedtuple with methods to calculate matching and overlapping of
           streams including (or not) wildcards
:platform: Any
    """

    __slots__ = ()

    def __contains__(self, st):
        """Check if one Stream is contained in this Stream.

:param st: Stream which should checked for overlapping
:type st: :class:`~Stream`
:returns: Value specifying whether the given stream is contained in this one
:rtype: Bool
"""

        if (fnmatch.fnmatch(st.n, self.n) and
                fnmatch.fnmatch(st.s, self.s) and
                fnmatch.fnmatch(st.l, self.l) and
                fnmatch.fnmatch(st.c, self.c)):
            return True

        return False

    def strictMatch(self, other):
        """Returns a new Stream with a *reduction* of this one to force the
        matching of the specification received as an input.

:param other: :class:`~Stream` which should checked for overlapping
:type other: :class:`~Stream`
:returns: *reduced* version of this stream to match the one passed in
          the parameter
:rtype: :class:`~Stream`
"""

        res = list()
        for i in range(len(other)):
            if (self[i] is None) or (fnmatch.fnmatch(other[i], self[i])):
                res.append(other[i])
            else:
                res.append(self[i])

        return Stream(*tuple(res))

    def overlap(self, other):
        """Checks if there is an overlap between this stream and other one

:param other: :class:`~Stream` which should be checked for overlapping
:type other: :class:`~Stream`
:returns: Value specifying whether there is an overlap between this
          stream and the one in the parameter
:rtype: Bool
"""

        for i in range(len(other)):
            if ((self[i] is not None) and (other[i] is not None) and
                    not fnmatch.fnmatch(self[i], other[i]) and
                    not fnmatch.fnmatch(other[i], self[i])):
                return False
        return True


class TW(namedtuple('TW', ['start', 'end'])):
    """
:synopsis: Namedtuple with methods to perform calculations on timewindows
:platform: Any
    """

    __slots__ = ()

    # This method works with the "in" clause or with the "overlap" method
    def __contains__(self, otherTW):
        return self.overlap(otherTW)

    def overlap(self, otherTW):
        """Check if other TW is contained in this TW.

:param otherTW: timewindow which should be checked for overlapping
:type otherTW: :class:`~TW`
:returns: Value specifying whether there is an overlap between this
          timewindow and the one in the parameter
:rtype: Bool

.. example:: If a < b < c < d:
             TW(b, c) in TW(a, d) ==> True
             TW(a, c) in TW(b, d) ==> True
             TW(a, d) in TW(b, c) ==> True
             TW(a, b) in TW(c, d) ==> False
"""

        # Trivial case. otherTW goes from the beginning of time till the end
        if otherTW.start is None and otherTW.end is None:
            return True

        if otherTW.start is not None:
            auxStart = self.start if self.start is not None else \
                otherTW.start - datetime.timedelta(seconds=1)
            auxEnd = self.end if self.end is not None else \
                otherTW.start + datetime.timedelta(seconds=1)
            if (auxStart < otherTW.start < auxEnd):
                return True
            if otherTW.end is None and (otherTW.start < auxEnd):
                return True

        if otherTW.end is not None:
            auxStart = self.start if self.start is not None else \
                otherTW.end - datetime.timedelta(seconds=1)
            auxEnd = self.end if self.end is not None else \
                otherTW.end + datetime.timedelta(seconds=1)
            if (auxStart < otherTW.end < auxEnd):
                return True
            if otherTW.start is None and (auxStart < otherTW.end):
                return True

        return False

    def difference(self, otherTW):
        """Substract the timewindow specified in otherTW from this one and
        return the result in a list of TW. This does not modify the data in
        the current timewindow.

:param otherTW: timewindow which should be substracted from this one
:type otherTW: :class:`~TW`
:returns: Difference between this timewindow and the one in the
          parameter
:rtype: list of :class:`~TW`
"""

        result = []

        if otherTW.start is not None:
            if ((self.start is None and otherTW.start is not None) or
                    ((self.start is not None) and
                     (self.start < otherTW.start))):
                result.append(TW(self.start, otherTW.start))

        if otherTW.end is not None:
            if ((self.end is None and otherTW.end is not None) or
                    ((self.end is not None) and
                     (self.end > otherTW.end))):
                result.append(TW(otherTW.end, self.end))

        return result

    def intersection(self, otherTW):
        """Calculate the intersection between this TW and the one in the
        parameter. This does not modify the data in the current timewindow.

:param otherTW: timewindow which should be intersected with this one
:type otherTW: :class:`~TW`
:returns: Intersection between this timewindow and the one in the
          parameter
:rtype: :class:`~TW`
"""

        resSt = None
        resEn = None

        # Trivial case
        if otherTW.start is None and otherTW.end is None:
            return self

        if otherTW.start is not None:
            resSt = max(self.start, otherTW.start) if self.start is not None \
                else otherTW.start
        else:
            resSt = self.start

        if otherTW.end is not None:
            resEn = min(self.end, otherTW.end) if self.end is not None \
                else otherTW.end
        else:
            resEn = self.end

        return TW(resSt, resEn)


class Route(namedtuple('Route', ['address', 'tw', 'priority'])):
    """
:synopsis: Namedtuple including the information to define a :class:`~Route`
           (a URL, a timewindow and a priority)
:platform: Any
    """

    __slots__ = ()

    def overlap(self, otherRoute):
        if self.priority == otherRoute.priority:
            return self.tw.overlap(otherRoute.tw)
        return False

    def __contains__(self, pointTime):
        raise Exception('This should not be used! Switch to the TW method!')
        if pointTime is None:
            return True

        try:
            if (((self.tw.start is None) or (self.tw.start < pointTime)) and
                    ((self.tw.end is None) or (pointTime < self.tw.end))):
                return True
        except:
            pass
        return False

Route.__eq__ = lambda self, other: self.priority == other.priority
Route.__ne__ = lambda self, other: self.priority != other.priority
Route.__lt__ = lambda self, other: self.priority < other.priority
Route.__le__ = lambda self, other: self.priority <= other.priority
Route.__gt__ = lambda self, other: self.priority > other.priority
Route.__ge__ = lambda self, other: self.priority >= other.priority


class RouteMT(namedtuple('RouteMT', ['address', 'tw', 'priority',
                                     'service'])):
    """
:synopsis: Namedtuple including the information to define a route in relation
           to a particular service
:platform: Any
    """

    __slots__ = ()

    def __contains__(self, pointTime):
        raise Exception('This should not be used! Switch to the TW method!')
        if pointTime is None:
            return True

        try:
            if (((self.tw.start <= pointTime) or (self.tw.start is None)) and
                    ((pointTime <= self.tw.end) or (self.tw.end is None))):
                return True
        except:
            pass
        return False

RouteMT.__eq__ = lambda self, other: self.priority == other.priority
RouteMT.__ne__ = lambda self, other: self.priority != other.priority
RouteMT.__lt__ = lambda self, other: self.priority < other.priority
RouteMT.__le__ = lambda self, other: self.priority <= other.priority
RouteMT.__gt__ = lambda self, other: self.priority > other.priority
RouteMT.__ge__ = lambda self, other: self.priority >= other.priority


class RoutingException(Exception):
    pass


class RoutingCache(object):
    """
:synopsis: Manage routing information of streams read from an Arclink-XML file.
:platform: Linux (maybe also Windows)
    """

    def __init__(self, routingFile, invFile, masterFile=None, logs=Logs(2)):
        """RoutingCache constructor

:param routingFile: XML file with routing information
:type routingFile: str
:param invFile: XML file with full inventory information
:type invFile: str
:param masterFile: XML file with high priority routes at network level
:type masterFile: str
:param logs: Class providing the methods: error/warning/info/debug
:type logs: for instance, :class:`~wsgicomm.Logs`

"""

        # Save the logging object
        self.logs = logs

        # Arclink routing file in XML format
        self.routingFile = routingFile

        # Dictionary with all the routes
        self.routingTable = dict()

        # Dictionary with the seedlink routes
        self.slTable = dict()

        # Dictionary with the FDSN-WS station routes
        self.stTable = dict()

        # Create/load the cache the first time that we start
        if routingFile == 'auto':
            self.configArclink()
            self.routingFile = './routing.xml'

        #try:
        self.update()
        #except:
        #    self.configArclink()
        #    self.update()

        # Add inventory cache here, to be able to expand request if necessary
        self.invFile = invFile
        self.ic = InventoryCache(invFile)

        # Read the configuration file and checks when do we need to update
        # the routes
        config = ConfigParser.RawConfigParser()

        here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))
        updTime = config.get('Service', 'updateTime')

        auxL = list()
        for auxT in updTime.split():
            toAdd = datetime.datetime.strptime(auxT, '%H:%M')
            auxL.append(toAdd)

        # Configure the expected update moment of the day
        now = datetime.datetime.now()

        self.updTimes = sorted(auxL)
        self.nextUpd = None
        self.lastUpd = now
        secsDay = 60 * 60 * 24
        if auxL:
            self.nextUpd = min(enumerate([(x - now).total_seconds() %
                                          secsDay for x in self.updTimes]),
                               key=itemgetter(1))[0]

        if masterFile is None:
            return

        # Master routing file in XML format
        self.masterFile = masterFile

        # Dictionary with list of highest priority routes
        self.masterTable = dict()

        self.updateMT()

    def localConfig(self):
        """Returns the local routing configuration

:returns: Local routing information in Arclink-XML format
:rtype: str

"""

        with open(self.routingFile) as f:
            return f.read()

    def configArclink(self):
        """Connects via telnet to an Arclink server to get routing information.
The address and port of the server are read from ``routing.cfg``.
The data is saved in the file ``routing.xml``. Generally used to start
operating with an EIDA default configuration.

.. note::

    In the future this method should not be used and the configuration should
    be independent from Arclink. Namely, the ``routing.xml`` file must exist in
    advance.

        """

        # Functionality moved away from this module. Check updateAll.py.
        return
        # Check Arclink server that must be contacted to get a routing table
        config = ConfigParser.RawConfigParser()

        here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))
        arcServ = config.get('Arclink', 'server')
        arcPort = config.getint('Arclink', 'port')

        tn = telnetlib.Telnet(arcServ, arcPort)
        tn.write('HELLO\n')
        # FIXME The institution should be detected here. Shouldn't it?
        self.logs.info(tn.read_until('GFZ', 5))
        tn.write('user routing@eida\n')
        self.logs.debug(tn.read_until('OK', 5))
        tn.write('request routing\n')
        self.logs.debug(tn.read_until('OK', 5))
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
            stText = tn.read_until('END', 5)

            stStr = 'status='
            myStatus = stText[stText.find(stStr) + len(stStr):].split()[0]
            myStatus = myStatus.replace('"', '').replace("'", "")
            self.logs.debug(myStatus + '\n')

        if myStatus != 'OK':
            self.logs.error('Error! Request status is not OK.\n')
            return

        tn.write('download %s\n' % reqID)
        routTable = tn.read_until('END', 5)
        start = routTable.find('<')
        self.logs.info('Length: %s\n' % routTable[:start])

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

        self.logs.info('Configuration read from Arclink!\n')

    def __arc2DS(self, route):
        """Map from an Arclink address to a Dataselect one

:param route: Arclink route
:type route: str
:returns: Dataselect URL equivalent of the given Arclink route
:rtype: str
:raises: Exception
        """

        gfz = 'http://geofon.gfz-potsdam.de/fdsnws/dataselect/1/query'
        odc = 'http://www.orfeus-eu.org/fdsnws/dataselect/1/query'
        eth = 'http://eida.ethz.ch/fdsnws/dataselect/1/query'
        resif = 'http://ws.resif.fr/fdsnws/dataselect/1/query'
        ingv = 'http://webservices.rm.ingv.it/fdsnws/dataselect/1/query'
        bgr = 'http://eida.bgr.de/fdsnws/dataselect/1/query'
        lmu = 'http://erde.geophysik.uni-muenchen.de/fdsnws/' +\
            'dataselect/1/query'
        ipgp = 'http://eida.ipgp.fr/fdsnws/dataselect/1/query'
        neis = 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query'

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
        elif host.startswith('141.84.'):
            return lmu
        elif host.endswith('ipgp.fr'):
            return ipgp
        elif host.endswith('infp.ro'):
            return neis
        raise Exception('No Dataselect equivalent found for %s' % route)

    def getRoute(self, n='*', s='*', l='*', c='*', startD=None, endD=None,
                 service='dataselect', alternative=False):
        """Based on a stream(s) and a timewindow returns all the needed
information (URLs and parameters) to do the requests to different datacenters
(if needed) and be able to merge the returned data avoiding duplication.

:param n: Network code
:type n: str
:param s: Station code
:type s: str
:param l: Location code
:type l: str
:param c: Channel code
:type c: str
:param startD: Start date and time
:type startD: datetime
:param endD: End date and time
:type endD: datetime
:param service: Service from which you want to get information
:type service: str
:param alternative: Specifies whether alternative routes should be included
:type alternative: bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        secsDay = 60 * 60 * 24
        lU = self.lastUpd
        # First check whether the information should be updated or not
        if self.nextUpd is not None:
            #try:
            now = datetime.datetime.now()
            if len(self.updTimes) == 1:
                now2lastUpd = (now - lU).seconds % secsDay \
                    if lU else secsDay
                upd2lastUpd = (self.updTimes[0] - lU).seconds % secsDay \
                    if lU else secsDay

                # Check for more than one day or updateTime in the past
                if (((now - self.lastUpd) > datetime.timedelta(days=1)) or
                        (now2lastUpd > upd2lastUpd)):
                    self.logs.debug('now2lastUpd > upd2lastUpd : %s > %s\n'
                                    % (now2lastUpd, upd2lastUpd))
                    self.logs.info('Updating at %s!\n' % now)
                    self.updateAll()
                    self.lastUpd = now
                    self.logs.debug('Update successful at: %s\n' %
                                    self.lastUpd)
            else:
                self.logs.debug('Next update: %s\n' %
                                self.updTimes[self.nextUpd])
                self.logs.debug('Last update: %s\n' % lU)

                auxU = min(enumerate([(x - now).total_seconds() % secsDay
                                      for x in self.updTimes]),
                           key=itemgetter(1))[0]
                if ((auxU != self.nextUpd) or
                        ((now - lU) > datetime.timedelta(days=1))):
                    self.logs.info('Updating at %s!\n' % now.isoformat())
                    self.updateAll()
                    # and move to the next time
                    self.nextUpd = auxU
                    self.lastUpd = now
            #except:
            #    pass

        stream = Stream(n, s, l, c)
        tw = TW(startD, endD)

        # Give priority to the masterTable!
        try:
            masterRoute = self.getRouteMaster(n, tw=tw, service=service,
                                              alternative=alternative)
            for mr in masterRoute:
                for reqL in mr['params']:
                    reqL['sta'] = s
                    reqL['loc'] = l
                    reqL['cha'] = c
            return masterRoute
        except:
            pass

        result = None
        if service == 'arclink':
            result = self.getRouteArc(stream, tw, alternative)
        elif service == 'dataselect':
            result = self.getRouteDS(stream, tw, alternative)
        elif service == 'seedlink':
            result = self.getRouteSL(stream, alternative)
        elif service == 'station':
            result = self.getRouteST(stream, tw, alternative)

        if result is None:
            # Through an exception if there is an error
            raise RoutingException('Unknown service: %s' % service)

        # FIXME This could be done in the function that calls getRoute
        # That would be more clear.
        for r in result:
            for p in r['params']:
                if type(p['start']) == type(datetime.datetime.now()):
                    p['start'] = p['start'].isoformat('T')
                if type(p['end']) == type(datetime.datetime.now()):
                    p['end'] = p['end'].isoformat('T')

        return result

    def getRouteST(self, stream, tw, alternative=False):
        """Based on a :class:`~Stream` and a timewindow (:class:`~TW`) returns
all the needed
information (URLs and parameters) to request station data from different
datacenters (if needed) and be able to merge it avoiding duplication.
The :func:`~RoutingCache.getRouteDS` (Dataselect) method is used and the
URL is changed to the FDSN station service style.

:param stream: :class:`~Stream` definition including wildcards
:type stream: :class:`~Stream`
:param tw: Timewindow
:type tw: :class:`~TW`
:param alternative: Specifies whether alternative routes should be included
:type alternative: bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        result = self.getRouteDS(stream, tw, alternative)
        for item in result:
            item['name'] = 'station'
            item['url'] = item['url'].replace('dataselect', 'station')

        return result

    def getRouteDS(self, stream, tw, alternative=False):
        """Based on a :class:`~Stream` and a timewindow (:class:`~TW`) returns
all the needed information (URLs and parameters) to request waveforms from
different datacenters (if needed) and be able to merge it avoiding duplication.
The Arclink routing table is used to select the datacenters and a mapping is
used to translate the Arclink address to Dataselect address
(see :func:`~RoutingCache.__arc2DS`).

:param stream: :class:`~Stream` definition including wildcards
:type stream: :class:`~Stream`
:param tw: Timewindow
:type tw: :class:`~TW`
:param alternative: Specifies whether alternative routes should be included
:type alternative: bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        # Check if there are wildcards!
        if (('*' in stream.n + stream.s + stream.l + stream.c) or
                ('?' in stream.n + stream.s + stream.l + stream.c)):
            # Filter first by the attributes without wildcards
            subs = self.routingTable.keys()

            if (('*' not in stream.s) and ('?' not in stream.s)):
                subs = [k for k in subs if (k.s is None or k.s == '*' or
                                            k.s == stream.s)]

            if (('*' not in stream.n) and ('?' not in stream.n)):
                subs = [k for k in subs if (k.n is None or k.n == '*' or
                                            k.n == stream.n)]

            if (('*' not in stream.c) and ('?' not in stream.c)):
                subs = [k for k in subs if (k.c is None or k.c == '*' or
                                            k.c == stream.c)]

            if (('*' not in stream.l) and ('?' not in stream.l)):
                subs = [k for k in subs if (k.l is None or k.l == '*' or
                                            k.l == stream.l)]

            # Filter then by the attributes WITH wildcards
            if (('*' in stream.s) or ('?' in stream.s)):
                subs = [k for k in subs if (k.s is None or k.s == '*' or
                                            fnmatch.fnmatch(k.s, stream.s))]

            if (('*' in stream.n) or ('?' in stream.n)):
                subs = [k for k in subs if (k.n is None or k.n == '*' or
                                            fnmatch.fnmatch(k.n, stream.n))]

            if (('*' in stream.c) or ('?' in stream.c)):
                subs = [k for k in subs if (k.c is None or k.c == '*' or
                                            fnmatch.fnmatch(k.c, stream.c))]

            if (('*' in stream.l) or ('?' in stream.l)):
                subs = [k for k in subs if (k.l is None or k.l == '*' or
                                            fnmatch.fnmatch(k.l, stream.l))]

            # Alternative NEW approach based on number of wildcards
            orderS = [sum([3 for t in r if '*' in t]) for r in subs]
            orderQ = [sum([1 for t in r if '?' in t]) for r in subs]

            order = map(add, orderS, orderQ)

            orderedSubs = [x for (y, x) in sorted(zip(order, subs))]

            finalset = set()

            for r1 in orderedSubs:
                for r2 in finalset:
                    if r1.overlap(r2):
                        self.logs.warning('Overlap between %s and %s\n' %
                                          (r1, r2))
                        break
                else:
                    finalset.add(r1.strictMatch(stream))
                    continue

                # The break from 10 lines above jumps until this line in
                # order to do an expansion and try to add the expanded
                # streams
                # r1n, r1s, r1l, r1c = r1
                for rExp in self.ic.expand(r1.n, r1.s, r1.l, r1.c,
                                           tw.start, tw.end, True):
                    rExp = Stream(*rExp)
                    for r3 in finalset:
                        if rExp.overlap(r3):
                            msg = 'Stream %s discarded! Overlap with %s\n' % \
                                (rExp, r3)
                            self.logs.warning(msg)
                            break
                    else:
                        self.logs.warning('Adding expanded %s\n' % str(rExp))
                        if (rExp in stream):
                            finalset.add(rExp)

            result = RequestMerge()

            # In finalset I have all the streams (including expanded and
            # the ones with wildcards), that I need to request.
            # Now I need the URLs
            self.logs.debug(str(finalset) + '\n')

            while finalset:
                st = finalset.pop()
                resArc = self.getRouteArc(st, tw, alternative)

                # The cycle is done backwards because I could need to delete
                # the current route
                for i in range(len(resArc) - 1, -1, -1):
                    resArc[i]['name'] = 'dataselect'
                    try:
                        resArc[i]['url'] = self.__arc2DS(resArc[i]['url'])
                    except:
                        # No mapping between Arclink and Dataselect
                        # We should delete it from the result
                        del resArc[i]

                result.extend(resArc)

            # Check the coherency of the routes to set the return code
            if len(result) == 0:
                raise RoutingException('No routes have been found!')
                #raise WIContentError('No routes have been found!')

            return result

        # If there are NO wildcards
        result = self.getRouteArc(stream, tw, alternative)

        for i in range(len(result) - 1, -1, -1):
            result[i]['name'] = 'dataselect'
            try:
                result[i]['url'] = self.__arc2DS(result[i]['url'])
            except:
                del result[i]

        # Check the coherency of the routes to set the return code
        if len(result) == 0:
            raise RoutingException('No routes have been found!')
            #raise WIContentError('No routes have been found!')

        return result

    def getRouteMaster(self, n, tw, service='dataselect', alternative=False):
        """Looks for a high priority :class:`~Route` for a particular network.
This would provide the flexibility to incorporate new networks and override
the normal configuration.

:param n: Network code
:type n: str
:param tw: Timewindow
:type tw: :class:`~TW`
:param alternative: Specifies whether alternative routes should be included
:type alternative: Bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        result = list()
        realRoutes = None

        # Case 11
        if (n, None, None, None) in self.masterTable:
            realRoutes = self.masterTable[n, None, None, None]

        # Check that I found a route
        for r in realRoutes:
            # Check if the timewindow is encompassed in the returned dates
            if (tw in r.tw):
                # Filtering with the service parameter!
                if service == r.service:
                    result.append(r)
                    if not alternative:
                        break

        # If I found nothing raise 204
        if not len(result):
            raise RoutingException('No routes have been found!')
            #raise WIContentError('No routes have been found!')

        result2 = RequestMerge()
        for r in result:
            result2.append(service, r.address, r.priority if r.priority
                           is not None else '', n, None, None,
                           None, tw.start if tw.start is not None else '',
                           tw.end if tw.end is not None else '')

        return result2

    def getRouteSL(self, stream, alternative):
        """Based on a :class:`~Stream` returns all the neccessary information
(URLs and parameters) to connect to a Seedlink server shipping real-time
information of the specified streams. This method implements the following
table lookup for the Seedlink service::

                01 NET STA CHA LOC
                02 NET STA CHA ---
                03 NET STA --- LOC
                04 NET --- CHA LOC
                05 --- STA CHA LOC
                06 NET STA --- ---
                07 NET --- CHA ---
                08 NET --- --- LOC
                09 --- STA CHA ---
                09 --- STA --- LOC
                10 --- --- CHA LOC
                11 NET --- --- ---
                12 --- STA --- ---
                13 --- --- CHA ---
                14 --- --- --- LOC
                15 --- --- --- ---

:param stream: :class:`~Stream` definition including wildcards
:type stream: :class:`~Stream`
:param alternative: Specifies whether alternative routes should be included
:type alternative: bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        realRoute = None

        # Case 1
        if stream in self.slTable:
            realRoute = self.slTable[stream]

        # Case 2
        elif (stream.n, stream.s, '*', stream.c) in self.slTable:
            realRoute = self.slTable[stream.n, stream.s, '*', stream.c]

        # Case 3
        elif (stream.n, stream.s, stream.l, '*') in self.slTable:
            realRoute = self.slTable[stream.n, stream.s, stream.l, '*']

        # Case 4
        elif (stream.n, '*', stream.l, stream.c) in self.slTable:
            realRoute = self.slTable[stream.n, '*', stream.l, stream.c]

        # Case 5
        elif ('*', stream.s, stream.l, stream.c) in self.slTable:
            realRoute = self.slTable['*', stream.s, stream.l, stream.c]

        # Case 6
        elif (stream.n, stream.s, '*', '*') in self.slTable:
            realRoute = self.slTable[stream.n, stream.s, '*', '*']

        # Case 7
        elif (stream.n, '*', '*', stream.c) in self.slTable:
            realRoute = self.slTable[stream.n, '*', '*', stream.c]

        # Case 8
        elif (stream.n, '*', stream.l, '*') in self.slTable:
            realRoute = self.slTable[stream.n, '*', stream.l, '*']

        # Case 9
        elif ('*', stream.s, '*', stream.c) in self.slTable:
            realRoute = self.slTable['*', stream.s, '*', stream.c]

        # Case 10
        elif ('*', '*', stream.l, stream.c) in self.slTable:
            realRoute = self.slTable['*', '*', stream.l, stream.c]

        # Case 11
        elif (stream.n, '*', '*', '*') in self.slTable:
            realRoute = self.slTable[stream.n, '*', '*', '*']

        # Case 12
        elif ('*', stream.s, '*', '*') in self.slTable:
            realRoute = self.slTable['*', stream.s, '*', '*']

        # Case 13
        elif ('*', '*', '*', stream.c) in self.slTable:
            realRoute = self.slTable['*', '*', '*', stream.c]

        # Case 14
        elif ('*', '*', stream.l, '*') in self.slTable:
            realRoute = self.slTable['*', '*', stream.l, '*']

        # Case 15
        elif ('*', '*', '*', '*') in self.slTable:
            realRoute = self.slTable['*', '*', '*', '*']

        result = RequestMerge()
        if realRoute is None:
            raise RoutingException('No routes have been found!')
            #raise WIContentError('No routes have been found!')

        for route in realRoute:
            # Check that I found a route
            if route is not None:
                result.append('seedlink', route.address, route.priority,
                              stream, '', '')

                if not alternative:
                    break

        return result

    def getRouteArc(self, stream, tw, alternative=False):
        """Based on a :class:`~Stream` and a timewindow (:class:`~TW`)returns
all the needed information (URLs and parameters) split by hosting datacenter.

.. warning:
    This is not too useful because Arclink can already do automatically the
    splitting of the request. However, this is used by the others methods in
    order to see where the waveforms are being hosted and give the location of
    the other services under the assumption that the one providing the
    waveforms through Arclink will be also providing the data for Dataselect
    and Station.

The following table lookup is implemented for the Arclink service::

                01 NET STA CHA LOC
                02 NET STA CHA ---
                03 NET STA --- LOC
                04 NET --- CHA LOC
                05 --- STA CHA LOC
                06 NET STA --- ---
                07 NET --- CHA ---
                08 NET --- --- LOC
                09 --- STA CHA ---
                09 --- STA --- LOC
                10 --- --- CHA LOC
                11 NET --- --- ---
                12 --- STA --- ---
                13 --- --- CHA ---
                14 --- --- --- LOC
                15 --- --- --- ---

:param stream: :class:`~Stream` definition including wildcards
:type stream: :class:`~Stream`
:param tw: Timewindow
:type tw: :class:`~TW`
:param alternative: Specifies whether alternative routes should be included
:type alternative: Bool
:returns: URLs and parameters to request the data
:rtype: :class:`~RequestMerge`
:raises: RoutingException

        """

        realRoute = None

        # Case 1
        if stream in self.routingTable:
            realRoute = self.routingTable[stream]

        # Case 2
        elif (stream.n, stream.s, '*', stream.c) in self.routingTable:
            realRoute = self.routingTable[stream.n, stream.s, '*', stream.c]

        # Case 3
        elif (stream.n, stream.s, stream.l, '*') in self.routingTable:
            realRoute = self.routingTable[stream.n, stream.s, stream.l, '*']

        # Case 4
        elif (stream.n, '*', stream.l, stream.c) in self.routingTable:
            realRoute = self.routingTable[stream.n, '*', stream.l, stream.c]

        # Case 5
        elif ('*', stream.s, stream.l, stream.c) in self.routingTable:
            realRoute = self.routingTable['*', stream.s, stream.l, stream.c]

        # Case 6
        elif (stream.n, stream.s, '*', '*') in self.routingTable:
            realRoute = self.routingTable[stream.n, stream.s, '*', '*']

        # Case 7
        elif (stream.n, '*', '*', stream.c) in self.routingTable:
            realRoute = self.routingTable[stream.n, '*', '*', stream.c]

        # Case 8
        elif (stream.n, '*', stream.l, '*') in self.routingTable:
            realRoute = self.routingTable[stream.n, '*', stream.l, '*']

        # Case 9
        elif ('*', stream.s, '*', stream.c) in self.routingTable:
            realRoute = self.routingTable['*', stream.s, '*', stream.c]

        # Case 10
        elif ('*', '*', stream.l, stream.c) in self.routingTable:
            realRoute = self.routingTable['*', '*', stream.l, stream.c]

        # Case 11
        elif (stream.n, '*', '*', '*') in self.routingTable:
            realRoute = self.routingTable[stream.n, '*', '*', '*']

        # Case 12
        elif ('*', stream.s, '*', '*') in self.routingTable:
            realRoute = self.routingTable['*', stream.s, '*', '*']

        # Case 13
        elif ('*', '*', '*', stream.c) in self.routingTable:
            realRoute = self.routingTable['*', '*', '*', stream.c]

        # Case 14
        elif ('*', '*', stream.l, '*') in self.routingTable:
            realRoute = self.routingTable['*', '*', stream.l, '*']

        # Case 15
        elif ('*', '*', '*', '*') in self.routingTable:
            realRoute = self.routingTable['*', '*', '*', '*']

        result = RequestMerge()
        if realRoute is None:
            raise RoutingException('No routes have been found!')
            #raise WIContentError('No routes have been found!')

        # Requested timewindow
        setTW = set()
        setTW.add(tw)

        # We don't need to loop as routes are already ordered by
        # priority. Take the first one!
        while setTW:
            toProc = setTW.pop()
            self.logs.debug('Processing %s\n' % str(toProc))
            for ro in realRoute:
                # Check if the timewindow is encompassed in the returned dates
                self.logs.debug('%s in %s = %s\n' % (str(toProc),
                                                     str(ro.tw),
                                                     (toProc in ro.tw)))
                if (toProc in ro.tw):

                    # If the timewindow is not complete then add the missing
                    # ranges to the tw set.
                    for auxTW in toProc.difference(ro.tw):
                        self.logs.debug('Adding %s\n' % str(auxTW))
                        setTW.add(auxTW)

                    auxSt, auxEn = toProc.intersection(ro.tw)
                    result.append('arclink', ro.address,
                                  ro.priority if ro.priority is not
                                  None else '', stream,
                                  auxSt if auxSt is not None else '',
                                  auxEn if auxEn is not None else '')
                    # Unless alternative routes are needed I can stop here
                    if not alternative:
                        break
                    # To look for alternative routes do not look in the whole
                    # period once we found a principal route. Try only to look
                    # for alternative routes for THIS timewindow
                    else:
                        toProc = TW(auxSt, auxEn)

        return result

    def updateAll(self):
        """Read the three sources of routing and inventory information"""

        self.logs.debug('Entering updateAll()\n')
        self.update()
        if self.masterFile is not None:
            self.updateMT()
        # Add inventory cache here, to be able to expand request if necessary
        self.ic = InventoryCache(self.invFile)

    def updateMT(self):
        """Read the routes with highest priority and store them in memory.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """

        self.logs.debug('Entering updateMT()\n')
        # Just to shorten notation
        ptMT = self.masterTable

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            context = ET.iterparse(self.masterFile, events=("start", "end"))
        except IOError:
            msg = 'Error: masterTable.xml could not be opened.\n'
            self.logs.warning(msg)
            return

        # turn it into an iterator
        context = iter(context)

        # get the root element
        event, root = context.next()

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = 'The file parsed seems not to be a routing file (XML).\n'
            self.logs.error(msg)
            return

        # Extract the namespace from the root node
        namesp = root.tag[:-len('routing')]

        ptMT.clear()

        for event, route in context:
            # The tag of this node should be "route".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if route.tag == namesp + 'route':

                    # Extract the location code
                    try:
                        locationCode = route.get('locationCode')
                        if len(locationCode) == 0:
                            locationCode = None
                    except:
                        locationCode = None

                    # Extract the network code
                    try:
                        networkCode = route.get('networkCode')
                        if len(networkCode) == 0:
                            networkCode = None
                    except:
                        networkCode = None

                    # Extract the station code
                    try:
                        stationCode = route.get('stationCode')
                        if len(stationCode) == 0:
                            stationCode = None
                    except:
                        stationCode = None

                    # Extract the stream code
                    try:
                        streamCode = route.get('streamCode')
                        if len(streamCode) == 0:
                            streamCode = None
                    except:
                        streamCode = None

                    # Traverse through the sources
                    #for arcl in route.findall(namesp + 'dataselect'):
                    for arcl in route:
                        service = arcl.tag.replace(namesp, '')
                        # Extract the address
                        try:
                            address = arcl.get('address')
                            if len(address) == 0:
                                continue
                        except:
                            continue

                        # Extract the priority
                        try:
                            prio = arcl.get('priority')
                        except:
                            prio = None

                        try:
                            startD = arcl.get('start')
                            if len(startD):
                                startParts = startD.replace('-', ' ')
                                startParts = startParts.replace('T', ' ')
                                startParts = startParts.replace(':', ' ')
                                startParts = startParts.replace('.', ' ')
                                startParts = startParts.replace('Z', '')
                                startParts = startParts.split()
                                startD = datetime.datetime(*map(int,
                                                                startParts))
                            else:
                                startD = None
                        except:
                            startD = None
                            msg = 'Error while converting START attribute.\n'
                            self.logs.error(msg)

                        # Extract the end datetime
                        try:
                            endD = arcl.get('end')
                            if len(endD) == 0:
                                endD = None
                        except:
                            endD = None

                        try:
                            endD = arcl.get('end')
                            if len(endD):
                                endParts = endD.replace('-', ' ')
                                endParts = endParts.replace('T', ' ')
                                endParts = endParts.replace(':', ' ')
                                endParts = endParts.replace('.', ' ')
                                endParts = endParts.replace('Z', '').split()
                                endD = datetime.datetime(*map(int, endParts))
                            else:
                                endD = None
                        except:
                            endD = None
                            msg = 'Error while converting END attribute.\n'
                            self.logs.error(msg)

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)
                        tw = TW(startD, endD)

                        if st not in ptMT:
                            ptMT[st] = [RouteMT(address, tw, prio, service)]
                        else:
                            ptMT[st].append(RouteMT(address, tw, prio,
                                                    service))

                        arcl.clear()

                    route.clear()

                root.clear()

        # Order the routes by priority
        for keyDict in ptMT:
            ptMT[keyDict] = sorted(ptMT[keyDict])

    def update(self):
        """Read the routing file in XML format and store it in memory.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """

        self.logs.debug('Entering update()\n')

        # Just to shorten notation
        ptRT = self.routingTable
        ptSL = self.slTable
        ptST = self.stTable

        # Clear all previous information
        ptRT.clear()
        ptSL.clear()
        ptST.clear()

        here = os.path.dirname(__file__)
        with open(os.path.join(here, 'data/routing.bin')) as rMerged:
            self.routingTable, self.slTable, self.stTable = \
                pickle.load(rMerged)
