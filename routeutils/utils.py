"""Classes to be used by the Routing WS for EIDA.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2017 Javier Quinteros, GEOFON, GFZ Potsdam <geofon@gfz-potsdam.de>
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz-potsdam.de>, GEOFON, GFZ Potsdam
"""

import os
import sys
import datetime
import fnmatch
import telnetlib
from urlparse import urlparse
import xml.etree.cElementTree as ET
from time import sleep
from collections import namedtuple
from operator import itemgetter
import logging

# Try to be Python 3 compliant as much as we can
try:
    import cPickle as pickle
except ImportError:
    import pickle

# More Python 3 compatibility
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

# More Python 3 compatibility
try:
    import urllib.request as ul
except ImportError:
    import urllib2 as ul


def str2date(dStr):
    """Transform a string to a datetime.

    :param dStr: A datetime in ISO format.
    :type dStr: string
    :return: A datetime represented the converted input.
    :rtype: datetime
    """
    # In case of empty string
    if not len(dStr):
        return None

    dateParts = dStr.replace('-', ' ').replace('T', ' ')
    dateParts = dateParts.replace(':', ' ').replace('.', ' ')
    dateParts = dateParts.replace('Z', '').split()
    return datetime.datetime(*map(int, dateParts))


def checkOverlap(str1, routeList, str2, route):
    """Check overlap of routes from stream str1 and a route from str2.

    :param str1: First stream
    :type str1: Stream
    :param routeList: List of routes already present
    :type routeList: list
    :param str2: Second stream
    :type str2: Stream
    :param route: Route to be checked
    :type route: Route
    :rtype: boolean
    :returns: Value indicating if routes overlap for both streams
    """
    if str1.overlap(str2):
        for auxRoute in routeList:
            if auxRoute.overlap(route):
                return True

    return False


def getStationCache(st, rt):
    """Retrieve station name and location from a particular station service.

    :param st: Stream for which a cache should be saved.
    :type st: Stream
    :param rt: Route where this stream is archived.
    :type rt: Route
    :returns: Stations found in this route for this stream pattern.
    :rtype: list
    """
    query = '%s?format=text&net=%s&sta=%s&start=%s' % \
            (rt.address, st.n, st.s, rt.tw.start.isoformat())
    if rt.tw.end is not None:
        query = query + '&end=%s' % rt.tw.end.isoformat()

    logging.debug(query)
    req = ul.Request(query)
    try:
        u = ul.urlopen(req)
        buf = u.read()
    except ul.URLError as e:
        logging.warning('The URL does not seem to be a valid Station-WS')
        if hasattr(e, 'reason'):
            logging.warning('%s - Reason: %s\n' % (rt.address, e.reason))
        elif hasattr(e, 'code'):
            logging.warning('The server couldn\'t fulfill the request.')
            logging.warning('Error code: %s\n', e.code)
        return list()

    result = list()
    for line in buf.splitlines():
        if line.startswith('#'):
            continue
        lSplit = line.split('|')
        try:
            start = str2date(lSplit[6])
            endt = str2date(lSplit[7])
            result.append(Station(lSplit[1], float(lSplit[2]),
                          float(lSplit[3]), start, endt))
        except:
            logging.error('Error trying to add station: (%s, %s, %s, %s, %s)' %
                          (lSplit[1], lSplit[2], lSplit[3], lSplit[6],
                           lSplit[7]))
    # print(result)
    if not len(result):
        logging.warning('No stations found for streams %s in %s' %
                        (st, rt.address))
    return result


def cacheStations(routingTable, stationTable):
    """Loop for all station-WS and cache all station names and locations.

    :param routingTable: Routing table.
    :type routingTable: list
    :param stationTable: Cache with names and locations of stations.
    :type stationTable: list
    """
    ptRT = routingTable
    for st in ptRT.keys():
        # Set a default result
        result = None

        # Set with the domain from all routes related to this stream
        services = set(urlparse(rt.address).netloc for rt in ptRT[st])
        for rt in ptRT[st]:
            if rt.service == 'station':
                if result is None:
                    result = getStationCache(st, rt)
                else:
                    result.extend(getStationCache(st, rt))

        if result is None:
            logging.warning('No Station-WS defined for this stream! No cache!')
            # Set a default value so that things still work
            result = list()

        for service in services:
            try:
                stationTable[service][st] = result
            except KeyError:
                stationTable[service] = dict()
                stationTable[service][st] = result


def addVirtualNets(fileName, **kwargs):
    """Read the routing file in XML format and store its VNs in memory.

    All information related to virtual networks is read into a dictionary. Only
    the necessary attributes are stored. This relies on the idea
    that some other agent should update the routing file at
    regular periods of time.

    :param fileName: File with virtual networks to add to the routing table.
    :type fileName: str
    :param vnTable: Table with virtual networks where aliases should be added.
    :type vnTable: dict
    :returns: Updated table containing aliases from the input file.
    :rtype: dict
    """
    # VN table is empty (default)
    ptVN = kwargs.get('vnTable', dict())

    logs = logging.getLogger('addVirtualNets')
    logs.debug('Entering addVirtualNets()\n')

    vnHandle = None
    try:
        vnHandle = open(fileName, 'r')
    except:
        msg = 'Error: %s could not be opened.\n'
        logs.error(msg % fileName)
        return

    # Traverse through the virtual networks
    # get an iterable
    try:
        context = ET.iterparse(vnHandle, events=("start", "end"))
    except IOError as e:
        logs.error(str(e))
        return

    # turn it into an iterator
    context = iter(context)

    # get the root element
    if hasattr(context, 'next'):
        event, root = context.next()
    else:
        event, root = next(context)

    # Check that it is really an inventory
    if root.tag[-len('routing'):] != 'routing':
        msg = 'The file parsed seems not to be a routing file (XML).\n'
        logs.error(msg)
        return ptVN

    # Extract the namespace from the root node
    namesp = root.tag[:-len('routing')]

    for event, vnet in context:
        # The tag of this node should be "route".
        # Now it is not being checked because
        # we need all the data, but if we need to filter, this
        # is the place.
        #
        if event == "end":
            if vnet.tag == namesp + 'vnetwork':

                # Extract the network code
                try:
                    vnCode = vnet.get('networkCode')
                    if len(vnCode) == 0:
                        vnCode = None
                except:
                    vnCode = None

                # Traverse through the sources
                # for arcl in route.findall(namesp + 'dataselect'):
                for stream in vnet:
                    # Extract the networkCode
                    msg = 'Only the * wildcard is allowed in virtual nets.'
                    try:
                        net = stream.get('networkCode')
                        if (('?' in net) or
                                (('*' in net) and (len(net) > 1))):
                            logs.warning(msg)
                            continue
                    except:
                        net = '*'

                    # Extract the stationCode
                    try:
                        sta = stream.get('stationCode')
                        if (('?' in sta) or
                                (('*' in sta) and (len(sta) > 1))):
                            logs.warning(msg)
                            continue
                    except:
                        sta = '*'

                    # Extract the locationCode
                    try:
                        loc = stream.get('locationCode')
                        if (('?' in loc) or
                                (('*' in loc) and (len(loc) > 1))):
                            logs.warning(msg)
                            continue
                    except:
                        loc = '*'

                    # Extract the streamCode
                    try:
                        cha = stream.get('streamCode')
                        if (('?' in cha) or
                                (('*' in cha) and (len(cha) > 1))):
                            logs.warning(msg)
                            continue
                    except:
                        cha = '*'

                    try:
                        auxStart = stream.get('start')
                        startD = str2date(auxStart)
                    except:
                        startD = None
                        msg = 'Error while converting START attribute.\n'
                        logs.warning(msg)

                    try:
                        auxEnd = stream.get('end')
                        endD = str2date(auxEnd)
                    except:
                        endD = None
                        msg = 'Error while converting END attribute.\n'
                        logs.warning(msg)

                    if vnCode not in ptVN:
                        ptVN[vnCode] = [(Stream(net, sta, loc, cha),
                                         TW(startD, endD))]
                    else:
                        ptVN[vnCode].append((Stream(net, sta, loc, cha),
                                             TW(startD, endD)))

                    stream.clear()

                vnet.clear()

            # FIXME Probably the indentation below is wrong.
            root.clear()

    return ptVN


def addRoutes(fileName, **kwargs):
    """Read the routing file in XML format and store it in memory.

    All the routing information is read into a dictionary. Only the
    necessary attributes are stored. This relies on the idea
    that some other agent should update the routing file at
    regular periods of time.

    :param fileName: File with routes to add the the routing table.
    :type fileName: str
    :param ptRT: Routing Table where routes should be added to.
    :type ptRT: dict
    :returns: Updated routing table containing routes from the input file.
    :rtype: dict
    """
    # Routing table is empty (default)
    ptRT = kwargs.get('routingTable', dict())

    logs = logging.getLogger('addRoutes')
    logs.debug('Entering addRoutes(%s)\n' % fileName)

    # Default value is NOT to allow overlapping streams
    allowOverlaps = kwargs.get('allowOverlaps', False)

    logs.info('Overlaps between routes will ' +
              ('' if allowOverlaps else 'NOT ' + 'be allowed'))

    with open(fileName, 'r') as testFile:
        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            context = ET.iterparse(testFile, events=("start", "end"))
        except IOError:
            msg = 'Error: %s could not be parsed. Skipping it!\n' % fileName
            logs.error(msg)
            return ptRT

        # turn it into an iterator
        context = iter(context)

        # get the root element
        # More Python 3 compatibility
        if hasattr(context, 'next'):
            event, root = context.next()
        else:
            event, root = next(context)

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = '%s seems not to be a routing file (XML). Skipping it!\n' \
                % fileName
            logs.error(msg)
            return ptRT

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

                        # Do not allow "?" wildcard in the input, because it
                        # will be impossible to match with the user input if
                        # this also has a mixture of "*" and "?"
                        if '?' in locationCode:
                            logs.error('Wildcard "?" is not allowed!')
                            continue

                    except:
                        locationCode = '*'

                    # Extract the network code
                    try:
                        networkCode = route.get('networkCode')
                        if len(networkCode) == 0:
                            networkCode = '*'

                        # Do not allow "?" wildcard in the input, because it
                        # will be impossible to match with the user input if
                        # this also has a mixture of "*" and "?"
                        if '?' in networkCode:
                            logs.error('Wildcard "?" is not allowed!')
                            continue

                    except:
                        networkCode = '*'

                    # Extract the station code
                    try:
                        stationCode = route.get('stationCode')
                        if len(stationCode) == 0:
                            stationCode = '*'

                        # Do not allow "?" wildcard in the input, because it
                        # will be impossible to match with the user input if
                        # this also has a mixture of "*" and "?"
                        if '?' in stationCode:
                            logs.error('Wildcard "?" is not allowed!')
                            continue

                    except:
                        stationCode = '*'

                    # Extract the stream code
                    try:
                        streamCode = route.get('streamCode')
                        if len(streamCode) == 0:
                            streamCode = '*'

                        # Do not allow "?" wildcard in the input, because it
                        # will be impossible to match with the user input if
                        # this also has a mixture of "*" and "?"
                        if '?' in streamCode:
                            logs.error('Wildcard "?" is not allowed!')
                            continue

                    except:
                        streamCode = '*'

                    # Traverse through the sources
                    for serv in route:
                        assert serv.tag[:len(namesp)] == namesp

                        service = serv.tag[len(namesp):]
                        att = serv.attrib

                        # Extract the address (mandatory)
                        try:
                            address = att.get('address')
                            if len(address) == 0:
                                logs.error('Could not add %s' % att)
                                continue
                        except:
                            logs.error('Could not add %s' % att)
                            continue

                        try:
                            auxStart = att.get('start', None)
                            startD = str2date(auxStart)
                        except:
                            startD = None

                        # Extract the end datetime
                        try:
                            auxEnd = att.get('end', None)
                            endD = str2date(auxEnd)
                        except:
                            endD = None

                        # Extract the priority
                        try:
                            priority = att.get('priority', '99')
                            if len(priority) == 0:
                                priority = 99
                            else:
                                priority = int(priority)
                        except:
                            priority = 99

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)
                        tw = TW(startD, endD)
                        rt = Route(service, address, tw, priority)

                        try:
                            # Check the overlap between the routes to import
                            # and the ones already present in the main Routing
                            # table
                            addIt = True
                            logs.debug('[RT] Checking %s' % str(st))
                            for testStr in ptRT.keys():
                                # This checks the overlap of Streams and also
                                # of timewindows and priority
                                if checkOverlap(testStr, ptRT[testStr], st,
                                                rt):
                                    msg = '%s: Overlap between %s and %s!\n'\
                                        % (fileName, st, testStr)
                                    logs.error(msg)
                                    if not allowOverlaps:
                                        logs.error('Skipping %s\n' % str(st))
                                        addIt = False
                                    break

                            if addIt:
                                ptRT[st].append(rt)
                            else:
                                logs.warning('Skip %s - %s\n' % (st, rt))

                        except KeyError:
                            ptRT[st] = [rt]
                        serv.clear()

                    route.clear()

                root.clear()

    # Order the routes by priority
    for keyDict in ptRT:
        ptRT[keyDict] = sorted(ptRT[keyDict])

    return ptRT


# FIXME It is probably better to swap the first two parameters
def addRemote(fileName, url):
    """Read the routing file from a remote datacenter and store it in memory.

    All the routing information is read into a dictionary. Only the
    necessary attributes are stored.

    :param fileName: file where the routes should be saved
    :type fileName: str
    :param url: Base URL from the Routing Service at the remote datacenter
    :type url: str
    :raise: Exception

    """
    logs = logging.getLogger('addRemote')
    logs.debug('Entering addRemote(%s)\n' % os.path.basename(fileName))

    # Prepare Request
    req = ul.Request(url + '/localconfig')

    blockSize = 4096 * 100

    fileName = fileName + '.download'

    try:
        os.remove(fileName)
        logs.debug('Successfully removed %s\n' % fileName)
    except:
        pass

    # Connect to the proper Routing-WS
    try:
        u = ul.urlopen(req)

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

    except ul.URLError as e:
        logs.warning('The URL does not seem to be a valid Routing Service')
        if hasattr(e, 'reason'):
            logs.warning('%s/localconfig - Reason: %s\n' % (url, e.reason))
        elif hasattr(e, 'code'):
            logs.warning('The server couldn\'t fulfill the request.')
            logs.warning('Error code: %s\n', e.code)
        logs.warning('Retrying with a static configuration file')

        # Prepare Request without the "localconfig" method
        req = ul.Request(url)
        try:
            u = ul.urlopen(req)

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
        except ul.URLError as e:
            if hasattr(e, 'reason'):
                logs.error('%s - Reason: %s\n' % (url, e.reason))
            elif hasattr(e, 'code'):
                logs.error('The server couldn\'t fulfill the request.')
                logs.error('Error code: %s\n', e.code)
            # I have to return because there is no data. Otherwise, the old
            # data will be removed (see below).
            return

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
    """Extend a list to group data from many requests by datacenter.

    :platform: Any

    """

    __slots__ = ()

    def append(self, service, url, priority, stream, tw):
        """Append a new :class:`~Route` without repeating the datacenter.

        Overrides the *append* method of the inherited list. If another route
        for the datacenter was already added, the remaining attributes are
        appended in *params* for the datacenter. If this is the first
        :class:`~Route` for the datacenter, everything is added.

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
                                        'start': tw.start, 'end': tw.end,
                                        'priority': priority if priority
                                        is not None else ''})
        except:
            # Take a reference to the inherited *list* and do a normal append
            listPar = super(RequestMerge, self)

            listPar.append({'name': service, 'url': url,
                            'params': [{'net': stream.n, 'sta': stream.s,
                                        'loc': stream.l, 'cha': stream.c,
                                        'start': tw.start, 'end': tw.end,
                                        'priority': priority if priority
                                        is not None else ''}]})

    def index(self, service, url):
        """Check for the service and url specified in the parameters.

        This overrides the *index* method of the inherited list.

        :param service: Requests from (possibly) different datacenters to be
            added
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
        """Append all the items in :class:`~RequestMerge` grouped by datacenter.

        Overrides the *extend* method of the inherited list. If another route
        for the datacenter was already added, the remaining attributes are
        appended in *params* for the datacenter. If this is the first
        :class:`~Route` for the datacenter, everything is added.

        :param listReqM: Requests from (posibly) different datacenters to be
            added
        :type listReqM: list of :class:`~RequestMerge`

        """
        for r in listReqM:
            try:
                pos = self.index(r['name'], r['url'])
                self[pos]['params'].extend(r['params'])
            except:
                super(RequestMerge, self).append(r)


# FIXME Should I replace start and end for a TW?
class Station(namedtuple('Station', ['name', 'latitude', 'longitude', 'start',
                                     'end'])):
    """Namedtuple representing a Station.

    This is the minimum information which needs to be cached from a station in
    order to be able to apply a proper filter to the inventory when queries
    f.i. do not include the network name.
           name: station name
           latitude: latitude
           longitude: longitude

    :platform: Any

    """

    __slots__ = ()


class geoRectangle(namedtuple('geoRectangle', ['minlat', 'maxlat', 'minlon',
                   'maxlon'])):
    """Namedtuple representing a geographical rectangle.

           minlat: minimum latitude
           maxlat: maximum latitude
           minlon: minimum longitude
           maxlon: maximum longitude

    :platform: Any

    """

    __slots__ = ()

    def contains(self, lat, lon):
        """Check if the point belongs to the rectangle."""
        return True if ((self.minlat <= lat <= self.maxlat) and
                        (self.minlon <= lon <= self.maxlon)) else False


class Stream(namedtuple('Stream', ['n', 's', 'l', 'c'])):
    """Namedtuple representing a Stream.

    It includes methods to calculate matching and overlapping of streams
    including (or not) wildcards. Components are the usual to determine a
    stream:
           n: network
           s: station
           l: location
           c: channel

    :platform: Any

    """

    __slots__ = ()

    def toXMLopen(self, nameSpace='ns0', level=1):
        """Export the stream to XML representing a route.

        XML representation is incomplete and needs to be closed by the method
        toXMLclose.

        """
        conv = '%s<%s:route networkCode="%s" stationCode="%s" ' + \
            'locationCode="%s" streamCode="%s">\n'
        return conv % (' ' * level, nameSpace, self.n, self.s, self.l, self.c)

    def toXMLclose(self, nameSpace='ns0', level=1):
        """Close the XML representation of a route given by toXMLopen."""
        return '%s</%s:route>\n' % (' ' * level, nameSpace)

    def __contains__(self, st):
        """Check if one :class:`~Stream` is contained in this :class:`~Stream`.

        :param st: :class:`~Stream` which should checked for overlapping
        :type st: :class:`~Stream`
        :returns: Value specifying whether the given stream is contained in
            this one
        :rtype: Bool

        """
        if (fnmatch.fnmatch(st.n, self.n) and
                fnmatch.fnmatch(st.s, self.s) and
                fnmatch.fnmatch(st.l, self.l) and
                fnmatch.fnmatch(st.c, self.c)):
            return True

        return False

    def strictMatch(self, other):
        """Return a *reduction* of this stream to match what's been received.

        :param other: :class:`~Stream` which should be checked for overlaps
        :type other: :class:`~Stream`
        :returns: *reduced* version of this :class:`~Stream` to match the one
            passed in the parameter
        :rtype: :class:`~Stream`
        :raises: Exception

        """
        res = list()
        for i in range(len(other)):
            if (self[i] is None) or (fnmatch.fnmatch(other[i], self[i])):
                res.append(other[i])
            elif (other[i] is None) or (fnmatch.fnmatch(self[i], other[i])):
                res.append(self[i])
            else:
                raise Exception('No overlap or match between streams.')

        return Stream(*tuple(res))

    def overlap(self, other):
        """Check if there is an overlap between this stream and other one.

        :param other: :class:`~Stream` which should be checked for overlaps
        :type other: :class:`~Stream`
        :returns: Value specifying whether there is an overlap between this
                  stream and the one passed as a parameter
        :rtype: Bool

        """
        for i in range(len(other)):
            if ((self[i] is not None) and (other[i] is not None) and
                    not fnmatch.fnmatch(self[i], other[i]) and
                    not fnmatch.fnmatch(other[i], self[i])):
                return False
        return True


class TW(namedtuple('TW', ['start', 'end'])):
    """Namedtuple with methods to perform calculations on timewindows.

    Attributes are:
           start: Start datetime
           end: End datetime

    :platform: Any

    """

    __slots__ = ()

    # This method works with the "in" clause or with the "overlap" method
    def __contains__(self, otherTW):
        """Wrap of the overlap method to allow  the use of the "in" clause.

        :param otherTW: timewindow which should be checked for overlaps
        :type otherTW: :class:`~TW`
        :returns: Value specifying whether there is an overlap between this
            timewindow and the one in the parameter
        :rtype: Bool

        """
        return self.overlap(otherTW)

    def overlap(self, otherTW):
        """Check if the otherTW is contained in this :class:`~TW`.

        :param otherTW: timewindow which should be checked for overlapping
        :type otherTW: :class:`~TW`
        :returns: Value specifying whether there is an overlap between this
                  timewindow and the one in the parameter
        :rtype: Bool

        .. rubric:: Examples

        >>> y2011 = datetime(2011, 1, 1)
        >>> y2012 = datetime(2012, 1, 1)
        >>> y2013 = datetime(2013, 1, 1)
        >>> y2014 = datetime(2014, 1, 1)
        >>> TW(y2011, y2014).overlap(TW(y2012, y2013))
        True
        >>> TW(y2012, y2014).overlap(TW(y2011, y2013))
        True
        >>> TW(y2012, y2013).overlap(TW(y2011, y2014))
        True
        >>> TW(y2011, y2012).overlap(TW(y2013, y2014))
        False

        """
        def inOrder(a, b, c):
            if ((b is None) and (a is not None) and (c is not None)):
                return False

            # Here I'm sure that b is not None
            if (a is None and c is None):
                return True

            # Here I'm sure that b is not None
            if (b is None and c is None):
                return True

            # I also know that a or c are not None
            if a is None:
                return b < c

            if c is None:
                return a < b

            # The three are not None
            # print a, b, c, a < b, b < c, a < b < c
            return a < b < c

        def inOrder2(a, b, c):
            # The three are not None
            # print a, b, c, a < b, b < c, a < b < c
            return a <= b <= c

        # First of all check that the TWs are correctly created
        if ((self.start is not None) and (self.end is not None) and
                (self.start > self.end)):
            raise ValueError('Start greater than End: %s > %s' % (self.start,
                                                                  self.end))

        if ((otherTW.start is not None) and (otherTW.end is not None) and
                (otherTW.start > otherTW.end)):
            raise ValueError('Start greater than End %s > %s' % (otherTW.start,
                                                                 otherTW.end))

        minDT = datetime.datetime(1900, 1, 1)
        maxDT = datetime.datetime(3000, 1, 1)

        sStart = self.start if self.start is not None else minDT
        oStart = otherTW.start if otherTW.start is not None else minDT
        sEnd = self.end if self.end is not None else maxDT
        oEnd = otherTW.end if otherTW.end is not None else maxDT

        if inOrder2(oStart, sStart, oEnd) or \
                inOrder2(oStart, sEnd, oEnd):
            return True

        # Check if this is included in otherTW
        if inOrder2(oStart, sStart, sEnd):
                return inOrder2(sStart, sEnd, oEnd)

        # Check if otherTW is included in this one
        if inOrder2(sStart, oStart, oEnd):
                return inOrder2(oStart, oEnd, sEnd)

        if self == otherTW:
            return True

        raise Exception('TW.overlap unresolved %s:%s' % (self, otherTW))

    def difference(self, otherTW):
        """Substract otherTW from this TW.

        The result is a list of TW. This operation does not modify the data in
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
        """Calculate the intersection between otherTW and this TW.

        This operation does not modify the data in the current timewindow.

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

        if ((resSt is not None) and (resEn is not None) and (resSt >= resEn)):
            raise ValueError('Intersection is empty')

        return TW(resSt, resEn)


class Route(namedtuple('Route', ['service', 'address', 'tw', 'priority'])):
    """Namedtuple defining a :class:`~Route`.

    The attributes are
           service: service name
           address: a URL
           tw: timewindow
           priority: priority of the route

    :platform: Any

    """

    __slots__ = ()

    def toXML(self, nameSpace='ns0', level=2):
        """Export the Route to an XML representation."""
        return '%s<%s:%s address="%s" priority="%d" start="%s" end="%s" />\n' \
            % (' ' * level, nameSpace, self.service, self.address,
               self.priority, self.tw.start.isoformat()
               if self.tw.start is not None else '',
               self.tw.end.isoformat() if self.tw.end is not None else '')

    def overlap(self, otherRoute):
        """Check if there is an overlap between this route and otherRoute.

        :param other: :class:`~Stream` which should be checked for overlaps
        :type other: :class:`~Stream`
        :returns: Value specifying whether there is an overlap between this
                  stream and the one passed as a parameter
        :rtype: Bool

        """
        if ((self.priority == otherRoute.priority) and
                (self.service == otherRoute.service)):
            return self.tw.overlap(otherRoute.tw)
        return False

    def __contains__(self, pointTime):
        """DEPRECATED METHOD."""
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


class RoutingException(Exception):
    """Exception raised to flag a problem when searching for routes."""

    pass


# Define this just to shorten the notation
defRectangle = geoRectangle(-90, 90, -180, 180)


class RoutingCache(object):
    """Manage routing information of streams read from an Arclink-XML file.

    :platform: Linux (maybe also Windows)

    """

    def __init__(self, routingFile=None, masterFile=None,
                 config='routing.cfg'):
        """Constructor of RoutingCache.

        :param routingFile: XML file with routing information
        :type routingFile: str
        :param masterFile: XML file with high priority routes at network level
        :type masterFile: str
        :param config: File where the configuration must be read from
        :type config: str

        """
        # Save the logging object
        self.logs = logging.getLogger('RoutingCache')

        # Arclink routing file in XML format
        self.routingFile = routingFile

        # Arclink routing file in XML format
        self.configFile = config

        # Dictionary with all the routes
        self.routingTable = dict()
        self.logs.info('Reading routes from %s' % self.routingFile)
        self.logs.info('Reading configuration from %s' % self.configFile)
        self.logs.info('Reading masterTable from %s' % masterFile)

        # Dictionary with list of stations inside each virtual network
        self.vnTable = dict()

        if self.routingFile is not None:
            self.logs.info('Wait until the RoutingCache is updated...')
            self.update()
            self.logs.info('RoutingCache finished!')

        # Check update time
        # Configure the expected update moment of the day
        now = datetime.datetime.now()

        self.nextUpd = None
        self.lastUpd = now

        # Read the verbosity setting
        configP = configparser.RawConfigParser()
        if len(configP.read(config)):

            updTime = configP.get('Service', 'updateTime')

            auxL = list()
            for auxT in updTime.split():
                toAdd = datetime.datetime.strptime(auxT, '%H:%M')
                auxL.append(toAdd)

            self.updTimes = sorted(auxL)
            secsDay = 60 * 60 * 24

            # FIXME This hack disables the update time if python is old because
            # it has no "total_seconds".
            if sys.version_info[0] == 2 and sys.version_info[1] < 7:
                auxL = list()

            if auxL:
                self.nextUpd = min(enumerate([(x - now).total_seconds() %
                                              secsDay for x in self.updTimes]),
                                   key=itemgetter(1))[0]

        # Check for masterTable
        if masterFile is None:
            self.logs.warning('No masterTable selected')
        else:
            # Master routing file in XML format
            self.masterFile = masterFile

            # Dictionary with list of highest priority routes
            self.masterTable = dict()

            self.updateMT()

    def toXML(self, foutput, nameSpace='ns0'):
        """Export the RoutingCache to an XML representation."""
        header = """<?xml version="1.0" encoding="utf-8"?>
<ns0:routing xmlns:ns0="http://geofon.gfz-potsdam.de/ns/Routing/1.0/">
"""
        with open(foutput, 'w') as fo:
            fo.write(header)
            for st, lr in self.routingTable.iteritems():
                fo.write(st.toXMLopen())
                for r in lr:
                    fo.write(r.toXML())
                fo.write(st.toXMLclose())
            fo.write('</ns0:routing>')

    def localConfig(self):
        """Return the local routing configuration.

        :returns: Local routing information in Arclink-XML format
        :rtype: str

        """
        with open(self.routingFile) as f:
            return f.read()

    def configArclink(self):
        """Connect via telnet to an Arclink server to get routing information.

        Address and port of the server are read from the configuration file.
        The data is saved in the file ``routing.xml``. Generally used to start
        operating with an EIDA default configuration.

        .. deprecated:: 1.1

        This method should not be used and the configuration should be
        independent from Arclink. Namely, the ``routing.xml`` file must exist
        in advance.

        """
        # Functionality moved away from this module. Check updateAll.py.

        return
        # Check Arclink server that must be contacted to get a routing table
        config = configparser.RawConfigParser()
        msg = 'Method configArclink is deprecated and should NOT be used!'
        self.logs.warning(msg)

        here = os.path.dirname(__file__)
        config.read(os.path.join(here, self.config))
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
        """Map from an Arclink address to a Dataselect one.

        :param route: Arclink route
        :type route: str
        :returns: Dataselect URL equivalent of the given Arclink route
        :rtype: str
        :raises: Exception

        .. deprecated:: 1.1

        This method should not be used and the configuration should be
        independent from Arclink. Namely, the ``routing.xml`` file must exist
        in advance.

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
        niep = 'http://eida-sc3.infp.ro/fdsnws/dataselect/1/query'
        koeri = \
            'http://eida.koeri.boun.edu.tr/fdsnws/dataselect/1/query'

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
            return niep
        elif host.endswith('boun.edu.tr'):
            return koeri
        raise Exception('No Dataselect equivalent found for %s' % route)

    def __time2Update(self):
        secsDay = 60 * 60 * 24
        # First check whether the information should be updated or not
        if self.nextUpd is not None:
            lU = self.lastUpd
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
                    # Return a pointer to the first (and unique) position of
                    # the updTimes array
                    return 0
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
                    # Return a pointer to the position of the updTimes array
                    # which shows when should the next update take place
                    return auxU
        # No update should be made
        return None

    # FIXME Stream and TW should probably be built before calling this method
    def getRoute(self, stream, tw, service='dataselect', geoLoc=None,
                 alternative=False):
        """Return routes to request data for the stream and timewindow provided.

        Based on a stream(s) and a timewindow returns all the needed
        information (URLs and parameters) to do the requests to different
        datacenters (if needed) and be able to merge the returned data avoiding
        duplication.

        :param stream: :class:`~Stream` definition including wildcards
        :type stream: :class:`~Stream`
        :param tw: Timewindow
        :type tw: :class:`~TW`
        :param service: Service from which you want to get information
        :type service: str
        :param geoLoc: Rectangle to filter stations
        :type geoLoc: :class:`~geoRectangle`
        :param alternative: Specifies whether alternative routes should be
            included
        :type alternative: bool
        :returns: URLs and parameters to request the data
        :rtype: :class:`~RequestMerge`
        :raises: RoutingException

        """
        # Is important to check against None because 0 is a valid value with a
        # total different meaning
        t2u = self.__time2Update()
        if t2u is not None:
            self.updateAll()
            self.lastUpd = datetime.datetime.now()
            self.nextUpd = t2u
            self.logs.debug('Update successful at: %s\n' % self.lastUpd)

        # Give priority to the masterTable!
        try:
            masterRoute = self.getRouteMaster(stream.n, tw=tw, service=service,
                                              alternative=alternative)
            for mr in masterRoute:
                for reqL in mr['params']:
                    reqL['sta'] = stream.s
                    reqL['loc'] = stream.l
                    reqL['cha'] = stream.c
            return masterRoute
        except:
            pass

        # Convert from virtual network to real networks (if needed)
        strtwList = self.vn2real(stream, tw)
        self.logs.debug('Converting %s to %s' % (stream, strtwList))

        if not len(strtwList):
            msg = 'No routes found after resolving virtual network code.'
            raise RoutingException(msg)

        result = RequestMerge()
        for st, tw in strtwList:
            try:
                result.extend(self.getRouteDS(service, st, tw, geoLoc,
                                              alternative))
                # print 'result', result
            except ValueError:
                pass

            except RoutingException:
                pass

        if ((result is None) or (not len(result))):
            # Through an exception if there is an error
            raise RoutingException('Unknown service: %s' % service)

        return result

    def vn2real(self, stream, tw):
        """Transform from a virtual network code to a list of streams.

        :param stream: requested stream including virtual network code.
        :type stream: Stream
        :param tw: time window requested.
        :type tw: TW
        :returns: Streams and time windows of real network-station codes.
        :rtype: list
        """
        if stream.n not in self.vnTable.keys():
            return [(stream, tw)]

        # If virtual networks are defined with open start or end dates
        # or if there is no intersection, that is resolved in the try

        # Remove the virtual network code to avoid problems in strictMatch
        auxStr = ('*', stream.s, stream.l, stream.c)

        result = list()
        for strtw in self.vnTable[stream.n]:
            try:
                s = strtw[0].strictMatch(auxStr)
            except:
                # Overlap or match cannot be calculated between streams
                continue

            try:
                auxSt, auxEn = strtw[1].intersection(tw)
                t = TW(auxSt if auxSt is not None else None,
                       auxEn if auxEn is not None else None)
            except:
                continue

            result.append((s, t))

        return result

    def getRouteDS(self, service, stream, tw, geoLocation=None,
                   alternative=False):
        """Return routes to request data for the parameters specified.

        Based on a :class:`~Stream` and a timewindow (:class:`~TW`) returns
        all the needed information (URLs and parameters) to request waveforms
        from different datacenters (if needed) and be able to merge it avoiding
        duplication.

        :param service: Specifies the service is being looked for
        :type service: string
        :param stream: :class:`~Stream` definition including wildcards
        :type stream: :class:`~Stream`
        :param tw: Timewindow
        :type tw: :class:`~TW`
        :param geoLocation: Rectangle restricting the location of the station
        :type geoLocation: :class:`~geoRectangle`
        :param alternative: Specifies whether alternative routes should be
            included
        :type alternative: bool
        :returns: URLs and parameters to request the data
        :rtype: :class:`~RequestMerge`
        :raises: RoutingException, ValueError

        """
        # Create list to store results
        subs = list()
        subs2 = list()

        # Filter by stream
        for stRT in self.routingTable.keys():
            if stRT.overlap(stream):
                subs.append(stRT)

        # print 'subs', subs

        # Filter by service and timewindow
        for stRT in subs:
            priorities = list()
            for rou in self.routingTable[stRT]:
                # If it is the proper service and the timewindow coincides
                # with the one in the parameter, add the priority to use it
                # in the last check
                # FIXME The method overlap below does NOT work if I swap
                # rou.tw and tw. For instance, check with:
                # TW(start=None, end=None) TW(start=datetime(1993, 1, 1, 0, 0),
                # end=None)
                if (service == rou.service) and (rou.tw.overlap(tw)):
                    priorities.append(rou.priority)
                else:
                    priorities.append(None)

            if not len([x for x in priorities if x is not None]):
                continue

            if not alternative:
                # Retrieve only the lowest value of priority
                prio2retrieve = [min(x for x in priorities if x is not None)]
            else:
                # Retrieve all alternatives. Don't care about priorities
                prio2retrieve = [x for x in priorities if x is not None]

            # print prio2retrieve

            for pos, p in enumerate(priorities):
                if p not in prio2retrieve:
                    continue

                # Add tuples with (Stream, Route)
                subs2.append((stRT, self.routingTable[stRT][pos]))

                # If I don't want the alternative take only the first one
                # if not alternative:
                #     break

        # print 'subs2', subs2

        finalset = list()

        # Reorder to have higher priorities first
        priorities = [rt.priority for (st, rt) in subs2]
        subs3 = [x for (y, x) in sorted(zip(priorities, subs2))]

        # print 'subs3', subs3

        for (s1, r1) in subs3:
            for (s2, r2) in finalset:
                if s1.overlap(s2) and r1.tw.overlap(r2.tw):
                    if not alternative:
                        self.logs.error('%s OVERLAPS\n %s\n' %
                                        ((s1, r1), (s2, r2)))
                        break

                    # Check that the priority is different! Because all
                    # the other attributes are the same or overlap
                    if r1.priority == r2.priority:
                        self.logs.error('Overlap between %s and %s\n' %
                                        ((s1, r1), (s2, r2)))
                        break
            else:
                # finalset.add(r1.strictMatch(stream))
                finalset.append((s1, r1))
                continue

        result = RequestMerge()

        # In finalset I have all the streams (including expanded and
        # the ones with wildcards), that I need to request.
        # Now I need the URLs
        self.logs.debug('Selected streams and routes: %s\n' % finalset)

        while finalset:
            (st, ro) = finalset.pop()

            # Requested timewindow
            setTW = set()
            setTW.add(tw)

            # We don't need to loop as routes are already ordered by
            # priority. Take the first one!
            while setTW:
                toProc = setTW.pop()
                self.logs.debug('Processing %s\n' % str(toProc))

                # Check if the timewindow is encompassed in the returned dates
                self.logs.debug('%s in %s = %s\n' % (str(toProc),
                                                     str(ro.tw),
                                                     (toProc in ro.tw)))
                if (toProc in ro.tw):

                    # If the timewindow is not complete then add the missing
                    # ranges to the tw set.
                    for auxTW in toProc.difference(ro.tw):
                        # Skip the case that we fall always in the same time
                        # span
                        if auxTW == toProc:
                            break
                        self.logs.debug('Adding %s\n' % str(auxTW))
                        setTW.add(auxTW)

                    # Check here that the final result is compatible with the
                    # stations in cache
                    ptST = self.stationTable[urlparse(ro.address).netloc]
                    for cacheSt in ptST[st]:
                        # Trying to catch cases like (APE, AP*)
                        # print st
                        # print cacheSt

                        if (fnmatch.fnmatch(cacheSt.name, stream.s) and
                                ((geoLocation is None) or
                                 (geoLocation.contains(cacheSt.latitude,
                                                       cacheSt.longitude)))):
                            try:
                                auxSt, auxEn = toProc.intersection(ro.tw)
                                twAux = TW(auxSt if auxSt is not None else '',
                                           auxEn if auxEn is not None else '')
                                st2add = stream.strictMatch(st)
                                # In case that routes have to be filter by
                                # location, station names have to be expanded
                                if geoLocation is not None:
                                    st2add = st2add.strictMatch(
                                        Stream('*', cacheSt.name, '*', '*'))

                                # print('Add %s' % str(st2add))

                                result.append(service, ro.address, ro.priority
                                              if ro.priority is not None
                                              else '', st2add, twAux)
                            except:
                                pass

                            # If we don't filter by location, one route covers
                            # everything but if we do filter by location, we
                            # need to keep adding stations
                            if geoLocation is None:
                                break
                    else:
                        msg = "Skipping %s as station %s not in its cache"
                        logging.debug(msg % (str(stream.strictMatch(st)),
                                             stream.s))

        # Check the coherency of the routes to set the return code
        if len(result) == 0:
            raise RoutingException('No routes have been found!')

        return result

    def getRouteMaster(self, n, tw, service='dataselect', alternative=False):
        """Look for a high priority :class:`~Route` for a particular network.

        This would provide the flexibility to incorporate new networks and
        override the normal configuration.

        :param n: Network code
        :type n: string
        :param tw: Timewindow
        :type tw: :class:`~TW`
        :param service: Service (e.g. dataselect)
        :type service: string
        :param alternative: Specifies whether alternative routes should be
            included
        :type alternative: Bool
        :returns: URLs and parameters to request the data
        :rtype: :class:`~RequestMerge`
        :raises: RoutingException

        """
        result = list()
        realRoutes = None

        # Case 11
        if Stream(n, None, None, None) in self.masterTable.keys():
            realRoutes = self.masterTable[n, None, None, None]

        if realRoutes is None:
            raise RoutingException('No route for this network in masterTable!')

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
            # raise WIContentError('No routes have been found!')

        result2 = RequestMerge()
        for r in result:
            twAux = TW(tw.start if tw.start is not None else '',
                       tw.end if tw.end is not None else '')
            result2.append(service, r.address, r.priority if r.priority
                           is not None else '', Stream(n, None, None,
                                                       None), twAux)

        return result2

    def updateAll(self):
        """Read the two sources of routing information."""
        self.logs.debug('Entering updateAll()\n')
        self.update()

        if self.masterFile is not None:
            self.updateMT()

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

        mtHandle = None
        try:
            mtHandle = open(self.masterFile, 'r')
        except:
            msg = 'Error: %s could not be opened.\n'
            self.logs.error(msg % self.masterFile)
            return

        # Parse the routing file
        # Traverse through the networks
        # get an iterable
        try:
            context = ET.iterparse(mtHandle, events=("start", "end"))
        except IOError as e:
            self.logs.error(str(e))
            return

        # turn it into an iterator
        context = iter(context)

        # get the root element
        if hasattr(context, 'next'):
            event, root = context.next()
        else:
            event, root = next(context)

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
                    # for arcl in route.findall(namesp + 'dataselect'):
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
                            auxStart = arcl.get('start')
                            startD = str2date(auxStart)
                        except:
                            startD = None
                            msg = 'Error while converting START attribute.\n'
                            self.logs.error(msg)

                        try:
                            auxEnd = arcl.get('end')
                            endD = str2date(auxEnd)
                        except:
                            endD = None
                            msg = 'Error while converting END attribute.\n'
                            self.logs.error(msg)

                        # Append the network to the list of networks
                        st = Stream(networkCode, stationCode, locationCode,
                                    streamCode)
                        tw = TW(startD, endD)
                        rt = Route(service, address, tw, prio)

                        if st not in ptMT:
                            ptMT[st] = [rt]
                        else:
                            ptMT[st].append(rt)

                        arcl.clear()

                    route.clear()

                root.clear()

        # Order the routes by priority
        for keyDict in ptMT:
            ptMT[keyDict] = sorted(ptMT[keyDict])

    def updateVN(self):
        """Read the virtual networks defined.

        Stations listed in each virtual network are read into a dictionary.
        Only the necessary attributes are stored. This relies on the idea
        that some other agent should update the routing file at
        a regular period of time.

        """
        self.logs.debug('Entering updateVN()\n')
        # Just to shorten notation
        ptVN = self.vnTable

        vnHandle = None
        try:
            vnHandle = open(self.routingFile, 'r')
        except:
            msg = 'Error: %s could not be opened.\n'
            self.logs.error(msg % self.routingFile)
            return

        # Traverse through the virtual networks
        # get an iterable
        try:
            context = ET.iterparse(vnHandle, events=("start", "end"))
        except IOError as e:
            self.logs.error(str(e))
            return

        # turn it into an iterator
        context = iter(context)

        # get the root element
        if hasattr(context, 'next'):
            event, root = context.next()
        else:
            event, root = next(context)

        # Check that it is really an inventory
        if root.tag[-len('routing'):] != 'routing':
            msg = 'The file parsed seems not to be a routing file (XML).\n'
            self.logs.error(msg)
            return

        # Extract the namespace from the root node
        namesp = root.tag[:-len('routing')]

        ptVN.clear()

        for event, vnet in context:
            # The tag of this node should be "route".
            # Now it is not being checked because
            # we need all the data, but if we need to filter, this
            # is the place.
            #
            if event == "end":
                if vnet.tag == namesp + 'vnetwork':

                    # Extract the network code
                    try:
                        vnCode = vnet.get('networkCode')
                        if len(vnCode) == 0:
                            vnCode = None
                    except:
                        vnCode = None

                    # Traverse through the sources
                    # for arcl in route.findall(namesp + 'dataselect'):
                    for stream in vnet:
                        # Extract the networkCode
                        msg = 'Only the * wildcard is allowed in virtual nets.'
                        try:
                            net = stream.get('networkCode')
                            if (('?' in net) or
                                    (('*' in net) and (len(net) > 1))):
                                self.logs.warning(msg)
                                continue
                        except:
                            net = '*'

                        # Extract the stationCode
                        try:
                            sta = stream.get('stationCode')
                            if (('?' in sta) or
                                    (('*' in sta) and (len(sta) > 1))):
                                self.logs.warning(msg)
                                continue
                        except:
                            sta = '*'

                        # Extract the locationCode
                        try:
                            loc = stream.get('locationCode')
                            if (('?' in loc) or
                                    (('*' in loc) and (len(loc) > 1))):
                                self.logs.warning(msg)
                                continue
                        except:
                            loc = '*'

                        # Extract the streamCode
                        try:
                            cha = stream.get('streamCode')
                            if (('?' in cha) or
                                    (('*' in cha) and (len(cha) > 1))):
                                self.logs.warning(msg)
                                continue
                        except:
                            cha = '*'

                        try:
                            auxStart = stream.get('start')
                            startD = str2date(auxStart)
                        except:
                            startD = None
                            msg = 'Error while converting START attribute.\n'
                            self.logs.error(msg)

                        try:
                            auxEnd = stream.get('end')
                            endD = str2date(auxEnd)
                        except:
                            endD = None
                            msg = 'Error while converting END attribute.\n'
                            self.logs.error(msg)

                        if vnCode not in ptVN:
                            ptVN[vnCode] = [(Stream(net, sta, loc, cha),
                                             TW(startD, endD))]
                        else:
                            ptVN[vnCode].append((Stream(net, sta, loc, cha),
                                                 TW(startD, endD)))

                        stream.clear()

                    vnet.clear()

                # FIXME Probably the indentation below is wrong.
                root.clear()

    def update(self):
        """Read the routing data from the file saved by the off-line process.

        All the routing information is read into a dictionary. Only the
        necessary attributes are stored. This relies on the idea that some
        other agent should update the routing data at a regular period of time.

        """
        self.logs.debug('Entering update()\n')

        # Otherwise, default value
        synchroList = ''
        allowOverlaps = False

        try:
            config = configparser.RawConfigParser()
            self.logs.debug(self.configFile)
            with open(self.configFile) as c:
                config.readfp(c)

            if 'synchronize' in config.options('Service'):
                synchroList = config.get('Service', 'synchronize')
        except:
            pass

        try:
            if 'allowOverlaps' in config.options('Service'):
                allowOverlaps = config.getboolean('Service', 'allowoverlap')
        except:
            pass

        self.logs.debug(synchroList)
        self.logs.debug('allowOverlaps: %s' % allowOverlaps)

        # Just to shorten notation
        ptRT = self.routingTable
        ptVN = self.vnTable

        # Clear all previous information
        ptRT.clear()
        ptVN.clear()
        try:
            binFile = self.routingFile + '.bin'
            with open(binFile) as rMerged:
                self.routingTable, self.stationTable, self.vnTable = \
                    pickle.load(rMerged)
        except:
            ptRT = addRoutes(self.routingFile, allowOverlaps=allowOverlaps)
            ptVN = addVirtualNets(self.routingFile)
            # Loop for the datacenters which should be integrated
            for line in synchroList.splitlines():
                if not len(line):
                    break
                self.logs.debug(str(line.split(',')))
                dcid, url = line.split(',')

                if os.path.exists(os.path.join(os.getcwd(), 'data',
                                               'routing-%s.xml' %
                                               dcid.strip())):
                    # addRoutes should return no Exception ever and skip
                    # a problematic file returning a coherent version of the
                    # routes
                    self.logs.debug('Routes in table: %s' % len(ptRT))
                    self.logs.debug('Adding REMOTE %s' % dcid)
                    ptRT = addRoutes(os.path.join(os.getcwd(), 'data',
                                                  'routing-%s.xml' %
                                                  dcid.strip()),
                                     routingTable=ptRT,
                                     allowOverlaps=allowOverlaps)
                    ptVN = addRoutes(os.path.join(os.getcwd(), 'data',
                                                  'routing-%s.xml' %
                                                  dcid.strip()),
                                     vnTable=ptVN)

            # Set here self.stationTable
            self.stationTable = dict()
            cacheStations(ptRT, self.stationTable)

            with open(binFile, 'wb') \
                    as finalRoutes:
                self.logs.debug('Writing %s\n' % binFile)
                pickle.dump((ptRT, self.stationTable, ptVN), finalRoutes)
                self.routingTable = ptRT
