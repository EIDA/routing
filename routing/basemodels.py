"""BaseModels to be used by the Routing WS for EIDA.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

   :Copyright:
       2014-2025 GFZ Helmholtz Centre for Geosciences, Potsdam, Germany
   :License:
       GPLv3
   :Platform:
       Linux

.. moduleauthor:: Javier Quinteros <javier@gfz.de>, GEOFON, GFZ Potsdam
"""

from pydantic import BaseModel
from pydantic import constr
from pydantic import Field
from pydantic import model_validator
from datetime import datetime
from typing import Union
from typing import List
from fnmatch import fnmatch
from pydantic import RootModel


class Station(BaseModel):
    """Namedtuple representing a Station.

    This is the minimum information which needs to be cached from a station in
    order to be able to apply a proper filter to the inventory when queries
    f.i. do not include the network name.
           name: station name
           latitude: latitude
           longitude: longitude
    """
    name: constr(min_length=1, max_length=5, to_upper=True, strip_whitespace=True)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    start: datetime
    end: Union[datetime, None] = Field(default=None)


class GeoRectangle(BaseModel):
    """Namedtuple representing a geographical rectangle.

           minlat: minimum latitude
           maxlat: maximum latitude
           minlon: minimum longitude
           maxlon: maximum longitude

    :platform: Any

    """
    minlat: float = Field(ge=-90.0, le=90.0)
    maxlat: float = Field(ge=-90.0, le=90.0)
    minlon: float = Field(ge=-180.0, le=180.0)
    maxlon: float = Field(ge=-180.0, le=180.0)

    def contains(self, lat: float, lon: float) -> bool:
        """Check if the point belongs to the rectangle."""
        return True if ((self.minlat <= lat <= self.maxlat) and
                        (self.minlon <= lon <= self.maxlon)) else False


class TWBase(BaseModel):
    """Namedtuple with methods to perform calculations on timewindows.

    Attributes are:
           start: Start datetime
           end: End datetime
    """
    start: datetime = Field(default=datetime(1900, 1, 1))
    end: Union[datetime, None] = Field(default=None)

    @model_validator(mode='after')
    def check_start_end_order(self):
        if (self.end is not None) and self.start >= self.end:
            raise ValueError('Error: "start" should be before "end"')
        return self


class TW(TWBase):
    """Namedtuple with methods to perform calculations on timewindows.

    Attributes are:
           start: Start datetime
           end: End datetime
    """
    # This method works with the "in" clause or with the "overlap" method
    def __contains__(self, othertw: TWBase) -> bool:
        """Wrap of the overlap method to allow  the use of the "in" clause.

        :param otherTW: timewindow which should be checked for overlaps
        :type otherTW: :class:`~TW`
        :returns: Value specifying whether there is an overlap between this
            timewindow and the one in the parameter
        :rtype: Bool

        """
        return self.overlap(othertw)

    def overlap(self, othertw: TWBase) -> bool:
        """Check if the othertw is contained in this :class:`~TW`.

        :param othertw: timewindow which should be checked for overlapping
        :type othertw: :class:`~TW`
        :returns: Value specifying whether there is an overlap between this
                  timewindow and the one in the parameter
        :rtype: Bool
        :raises: ValueError if start is greater than end

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
        def inOrder2(a: datetime, b: datetime, c: datetime) -> bool:
            # The three are not None
            # print a, b, c, a < b, b < c, a < b < c
            return a <= b <= c

        # minDT = datetime(1900, 1, 1)
        maxDT = datetime(3000, 1, 1)

        sStart = self.start
        oStart = othertw.start
        sEnd = self.end if self.end is not None else maxDT
        oEnd = othertw.end if othertw.end is not None else maxDT

        if inOrder2(oStart, sStart, oEnd) or \
                inOrder2(oStart, sEnd, oEnd):
            return True

        # Check if this is included in otherTW
        if inOrder2(oStart, sStart, sEnd):
            return inOrder2(sStart, sEnd, oEnd)

        # Check if otherTW is included in this one
        if inOrder2(sStart, oStart, oEnd):
            return inOrder2(oStart, oEnd, sEnd)

        if self == othertw:
            return True

        raise Exception('TW.overlap unresolved %s:%s' % (self, othertw))

    def difference(self, othertw: TWBase) -> List[TWBase]:
        """Substract othertw from this TW.

        The result is a list of TW. This operation does not modify the data in
        the current timewindow.

        :param othertw: timewindow which should be substracted from this one
        :type othertw: :class:`~TW`
        :returns: Difference between this timewindow and the one in the
                  parameter
        :rtype: list of :class:`~TW`

        """
        result = []

        if self.start < othertw.start:
            if self.end is not None:
                result.append(TW(start=self.start, end=min(self.end, othertw.start)))
            else:
                result.append(TW(start=self.start, end=othertw.start))

        if othertw.end is None:
            return result

        if (self.end is None) or ((self.end is not None) and (self.end > othertw.end)):
            result.append(TW(start=othertw.end, end=self.end))
        return result

    def intersection(self, othertw: TWBase) -> TWBase:
        """Calculate the intersection between othertw and this TW.

        This operation does not modify the data in the current timewindow.

        :param othertw: timewindow which should be intersected with this one
        :type othertw: :class:`~TW`
        :returns: Intersection between this timewindow and the one in the
                  parameter
        :rtype: :class:`~TW`

        """
        resst = max(self.start, othertw.start)
        if othertw.end is not None:
            resen = min(self.end, othertw.end) if self.end is not None else othertw.end
        else:
            resen = self.end

        if (resen is not None) and (resst >= resen):
            raise ValueError('Intersection is empty')

        return TW(start=resst, end=resen)


class StreamBase(BaseModel):
    """Namedtuple representing a Stream.

    It includes methods to calculate matching and overlapping of streams
    including (or not) wildcards. Components are the usual to determine a
    stream:
           n: network
           s: station
           l: location
           c: channel
    """
    n: str = constr(min_length=1, max_length=10, to_upper=True, strip_whitespace=True)
    s: str = constr(min_length=1, max_length=5, to_upper=True, strip_whitespace=True)
    l: str = constr(min_length=1, max_length=2, to_upper=True, strip_whitespace=True)
    c: str = constr(min_length=1, max_length=3, to_upper=True, strip_whitespace=True)
    model_config = {"frozen": True}  # Enables hashing


class Stream(StreamBase):
    def toxmlopen(self, namespace: str = 'ns0', level: int = 1) -> str:
        """Export the stream to XML representing a route.

        XML representation is incomplete and needs to be closed by the method
        toxmlclose.
        """
        conv = '%s<%s:route networkCode="%s" stationCode="%s" ' + \
            'locationCode="%s" streamCode="%s">\n'
        return conv % (' ' * level, namespace, self.n, self.s, self.l, self.c)

    def toxmlclose(self, namespace: str = 'ns0', level: int = 1) -> str:
        """Close the XML representation of a route given by toxmlopen."""
        return '%s</%s:route>\n' % (' ' * level, namespace)

    def __contains__(self, st: StreamBase) -> bool:
        """Check if one :class:`~Stream` is contained in this :class:`~Stream`.

        :param st: :class:`~Stream` which should checked for overlapping
        :type st: :class:`~Stream`
        :returns: Value specifying whether the given stream is contained in
            this one
        :rtype: Bool

        """
        if (fnmatch(st.n, self.n) and
                fnmatch(st.s, self.s) and
                fnmatch(st.l, self.l) and
                fnmatch(st.c, self.c)):
            return True
        return False

    def strictmatch(self, other: StreamBase) -> StreamBase:
        """Return a *reduction* of this stream to match what's been received.

        :param other: :class:`~Stream` which should be checked for overlaps
        :type other: :class:`~Stream`
        :returns: *reduced* version of this :class:`~Stream` to match the one
            passed in the parameter
        :rtype: :class:`~Stream`
        :raises: Exception

        """
        res = list()

        if fnmatch(other.n, self.n):
            res.append(other.n)
        elif fnmatch(self.n, other.n):
            res.append(self.n)
        else:
            raise Exception('No overlap or match at network level.')

        if fnmatch(other.s, self.s):
            res.append(other.s)
        elif fnmatch(self.s, other.s):
            res.append(self.s)
        else:
            raise Exception('No overlap or match at station level.')

        if fnmatch(other.l, self.l):
            res.append(other.l)
        elif fnmatch(self.l, other.l):
            res.append(self.l)
        else:
            raise Exception('No overlap or match at location level.')

        if fnmatch(other.c, self.c):
            res.append(other.c)
        elif fnmatch(self.c, other.c):
            res.append(self.c)
        else:
            raise Exception('No overlap or match at channel level.')
        return Stream(n=res[0], s=res[1], l=res[2], c=res[3])

    def overlap(self, other: StreamBase) -> bool:
        """Check if there is an overlap between this stream and other one.

        :param other: :class:`~Stream` which should be checked for overlaps
        :type other: :class:`~Stream`
        :returns: Value specifying whether there is an overlap between this
                  stream and the one passed as a parameter
        :rtype: Bool

        """
        if not fnmatch(self.n, other.n) and not fnmatch(other.n, self.n):
            return False
        if not fnmatch(self.s, other.s) and not fnmatch(other.s, self.s):
            return False
        if not fnmatch(self.l, other.l) and not fnmatch(other.l, self.l):
            return False
        if not fnmatch(self.c, other.c) and not fnmatch(other.c, self.c):
            return False
        return True


class RouteBase(BaseModel):
    """Namedtuple defining a :class:`~Route`.

    The attributes are
           service: service name
           address: a URL
           tw: timewindow
           priority: priority of the route
    """
    service: str
    address: str
    tw: TW
    priority: int = Field(ge=1, default=1)


class Route(RouteBase):
    def toxml(self, namespace: str = 'ns0', level: int = 2) -> str:
        """Export the Route to an XML representation."""
        return '%s<%s:%s address="%s" priority="%d" start="%s" end="%s" />\n' \
            % (' ' * level, namespace, self.service, self.address,
               self.priority, self.tw.start.isoformat()
               if self.tw.start is not None else '',
               self.tw.end.isoformat() if self.tw.end is not None else '')

    def overlap(self, otherroute: RouteBase) -> bool:
        """Check if there is an overlap between this route and otherroute.

        :param otherroute: :class:`~Route` which should be checked for overlaps
        :type otherroute: :class:`~Route`
        :returns: Value specifying whether there is an overlap between this
                  stream and the one passed as a parameter
        :rtype: Bool

        """
        if ((self.priority == otherroute.priority) and
                (self.service == otherroute.service)):
            return self.tw.overlap(otherroute.tw)
        return False

    def __eq__(self, other: RouteBase) -> bool:
        return self.priority == other.priority

    def __ne__(self, other: RouteBase) -> bool:
        return self.priority != other.priority

    def __lt__(self, other: RouteBase) -> bool:
        return self.priority < other.priority

    def __le__(self, other: RouteBase) -> bool:
        return self.priority <= other.priority

    def __gt__(self, other: RouteBase) -> bool:
        return self.priority > other.priority

    def __ge__(self, other: RouteBase) -> bool:
        return self.priority >= other.priority


class VirtualNetworks(RootModel):
    root: dict[str, list[tuple[Stream, TW]]]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, key, value):
        self.root[key] = value

    def clear(self):
        self.root = {}

    def __len__(self):
        return len(self.root)
