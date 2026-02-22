"""Routing Service for EIDA.

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
import json
import uvicorn
from fastapi import FastAPI
from fastapi import Response
from fastapi.responses import HTMLResponse
from fastapi.responses import PlainTextResponse
from fastapi.responses import JSONResponse
import os
import cgi
from datetime import datetime
from datetime import date
from datetime import timedelta
import logging
import configparser
from basemodels import Stream
from basemodels import TW
from basemodels import GeoRectangle
from utils import RequestMerge
from utils import RoutingCache
from utils import RoutingException
from utils import str2date
from utils import lsNSLC
from utils import applyFormat
from utils import __version__
from typing import Union
from typing import List
from typing import Literal



class XMLResponse(Response):
    media_type = "application/xml"

    def render(self, content) -> bytes:
        return super().render(content)


class Config(object):
    """Class reading the configuration of the Routing Service. It is based in the pythonic implementation
    of the Singleton design pattern."""
    config = None

    def __new__(cls):
        if cls.config is None:
            cfgfile = os.path.expanduser('routing.cfg')
            # Open configuration file
            config = configparser.RawConfigParser()
            config.read(cfgfile)

            cls.config = dict()
            # Read connection parameters
            cls.config['baseURL'] = config.get('Service', 'baseURL')
            cls.config['info'] = config.get('Service', 'info', fallback='')
            cls.config['allowoverlap'] = config.get('Service', 'allowoverlap', fallback=False)
            cls.config['verbosity'] = config.get('Service', 'verbosity', fallback='INFO')

            cls.config['synchronize'] = config.get('Service', 'synchronize', fallback=None)

            logging.info('Configuration read: %s' % Config)
        return cls.config


class Cache(object):
    routes = None

    def __new__(cls):
        if cls.routes is None:
            cls.routes = RoutingCache(os.path.expanduser('./data/routing.xml'),
                                      os.path.expanduser('./routing.cfg'))
        return cls.routes


routingws = FastAPI()


@routingws.get("/endpoints", response_class=PlainTextResponse)
async def rsendpoints():
    routingcache = Cache()
    result = routingcache.endpoints()
    return result


@routingws.get("/", response_class=HTMLResponse)
async def rsroot():
    """Show a help page"""
    with open(os.path.expanduser('./data/help.html')) as fin:
        htmlpage = fin.read().encode()
    return HTMLResponse(content=htmlpage, status_code=200)


@routingws.get("/version", response_class=PlainTextResponse)
async def rsversion():
    """Return the version of the Routing Service"""
    return __version__


@routingws.get("/info", response_class=PlainTextResponse)
async def rsinfo():
    """Return information about the content available in this Routing Service"""
    cfg = Config()
    return cfg['info']


@routingws.get("/application.wadl", response_class=XMLResponse)
async def rsapplicationwadl():
    """Show a help page"""
    cfg = Config()
    tomorrow = date.today() + timedelta(days=1)
    with open(os.path.expanduser('./data/application.wadl')) as fin:
        awpage = fin.read() % (cfg['baseURL'], tomorrow)
    return XMLResponse(content=awpage.encode(), status_code=200)


@routingws.get("/localconfig", response_class=XMLResponse)
async def rslocalconfig():
    """Show the local routes"""
    routingcache = Cache()
    result = routingcache.localConfig()
    return XMLResponse(content=result, status_code=200)


@routingws.get("/virtualnets", response_class=JSONResponse)
async def rsvirtualnets():
    """Show the virtual networks defined"""
    routingcache = Cache()
    result = routingcache.virtualNets()
    return result
    # return JSONResponse(content=result, status_code=200)


@routingws.get("/globalconfig", response_class=JSONResponse)
async def rsglobalconfig(outform: Literal['fdsn']):
    """Export all routes to FDSN"""
    if outform != 'fdsn':
        return JSONResponse(content={'message': 'Only format=FDSN is supported'},
                            status_code=400)
    routingcache = Cache()
    result = routingcache.globalConfig()
    return result


@routingws.get("/dc", response_class=JSONResponse)
async def rsdc():
    """Show information about the data centre"""
    with open(os.path.expanduser('~/routing/data/routing.json')) as fin:
        dcpage = json.load(fin)
    return dcpage


@routingws.get("/query")
async def rsqueryget(net: str = None, network: str = None, sta: str = None, station: str = None,
                     loc: str = None, location: str = None, cha: str = None, channel: str = None,
                     start: datetime = None, starttime: datetime = None,
                     end: datetime = None, endtime: datetime = None,
                     minlat: float = None, minlatitude: float = None,
                     maxlat: float = None, maxlatitude: float = None,
                     minlon: float = None, minlongitude: float = None,
                     maxlon: float = None, maxlongitude: float = None,
                     service: str = 'dataselect', format: Literal['json', 'get', 'post', 'xml'] = 'xml',
                     alternative: str = 'false', nodata: int = 204):
    """Process a request made via a GET method."""
    routingcache = Cache()

    try:
        # If CSV is True the result will be a list!
        net = simplifyparam(net, network, '*', csv=True)
        sta = simplifyparam(sta, station, '*', csv=True)
        loc = simplifyparam(loc, location, '*', csv=True)
        cha = simplifyparam(cha, channel, '*', csv=True)
        startt = simplifyparam(start, starttime, datetime(1900, 1, 1))
        endt = simplifyparam(end, endtime, None)
        minlati = simplifyparam(minlat, minlatitude, -90.0)
        maxlati = simplifyparam(maxlat, maxlatitude, 90.0)
        minlong = simplifyparam(minlon, minlongitude, -180.0)
        maxlong = simplifyparam(maxlon, maxlongitude, 180.0)
    except Exception as e:
        return PlainTextResponse(content=str(e), status_code=400)

    alt = False if alternative.lower() in ['false', '0'] else True
    if alt and (format=='get'):
        return PlainTextResponse(content='alternative=true and format=get are incompatible parameters',
                                 status_code=400)

    if (startt is not None) and (endt is not None) and (startt > endt):
        return PlainTextResponse(content='Start datetime cannot be greater than end datetime',
                                 status_code=400)

    if ((minlati == -90.0) and (maxlati == 90.0) and (minlong == -180.0) and
            (maxlong == 180.0)):
        geoLoc = None
    else:
        geoLoc = GeoRectangle(minlati, maxlati, minlong, maxlong)

    result = RequestMerge()
    # Expand lists in parameters (f.i., cha=BHZ,HHN) and yield all possible
    # values
    for (n, s, l, c) in lsNSLC(net, sta, loc, cha):
        try:
            st = Stream(n=n, s=s, l=l, c=c)
            tw = TW(start=startt, end=endt)
            result.extend(routingcache.getRoute(st, tw, service, geoLoc, alt))
        except RoutingException:
            pass

    if len(result) == 0:
        return PlainTextResponse(status_code=nodata)

    if format == 'xml':
        return XMLResponse(content=applyFormat(result, format), status_code=200)
    elif format == 'json':
        # FIXME There could be a problem here with the conversion from str to JSON
        return JSONResponse(content=applyFormat(result, format), status_code=200)
    elif format == 'get':
        return PlainTextResponse(content=applyFormat(result, format), status_code=200)
    elif format == 'post':
        return PlainTextResponse(content=applyFormat(result, format), status_code=200)
    return PlainTextResponse(content='Format %s not supported' % format, status_code=400)


@routingws.post("/query")
async def rsquerypost():
    pass


def simplifyparam(p1: Union[str, float, datetime], p2: Union[str, float, datetime],
                  default: Union[str, float, datetime, None], csv: bool = False) -> Union[str, datetime, float, List[str], None]:
    """Read two parameters and return the one that is valid or a default value if there is no one.

    The csv parameter is used to split the value in case of multiple values separated by commas. This means
    that the result will be a string if csv is False, and a list of string(s) if csv is True.
    """
    result = None
    # Empty parameter2 or both
    if p2 is None:
        result = p1 if p1 is not None else default
    elif p1 is None:
        # Empty parameter1
        result = p2

    if isinstance(result, str) and csv:
        # WARNING This converts the result from a string to a list with a string(s) if "cvs" is True
        return result.split(',')

    return result


def makeQueryPOST(postText) -> RequestMerge:
    """Process a request made via a POST method."""
    global routes

    # These are the parameters accepted appart from N.S.L.C
    extraParams = ['format', 'service', 'alternative', 'nodata',
                   'minlat', 'minlatitude',
                   'maxlat', 'maxlatitude',
                   'minlon', 'minlongitude',
                   'maxlon', 'maxlongitude']

    # Default values
    ser = 'dataselect'
    alt = False

    result = RequestMerge()
    # Check if we are still processing the header of the POST body. This has a
    # format like key=value, one per line.
    inHeader = True

    minlat = -90.0
    maxlat = 90.0
    minlon = -180.0
    maxlon = 180.0

    filterdefined = False
    for line in postText.splitlines():
        if not len(line):
            continue

        if inHeader and ('=' not in line):
            inHeader = False

        if inHeader:
            try:
                key, value = line.split('=')
                key = key.strip()
                value = value.strip()
            except Exception:
                msg = 'Wrong format detected while processing: %s' % line
                raise WIClientError(msg)

            if key not in extraParams:
                msg = 'Unknown parameter "%s"' % key
                raise WIClientError(msg)

            if key == 'service':
                ser = value
            elif key == 'alternative':
                alt = True if value.lower() == 'true' else False
            elif key == 'minlat':
                minlat = float(value.lower())
            elif key == 'maxlat':
                maxlat = float(value.lower())
            elif key == 'minlon':
                minlon = float(value.lower())
            elif key == 'maxlon':
                maxlon = float(value.lower())

            continue

        # I'm already in the main part of the POST body, where the streams are
        # specified
        filterdefined = True

        net, sta, loc, cha, start, endt = line.split()
        net = net.upper()
        sta = sta.upper()
        loc = loc.upper()
        try:
            if start.strip() == '*':
                start = None
            else:
                start = str2date(start)
        except Exception:
            msg = 'Error while converting %s to datetime' % start
            raise WIClientError(msg)

        try:
            if endt.strip() == '*':
                endt = None
            else:
                endt = str2date(endt)
        except Exception:
            msg = 'Error while converting %s to datetime' % endt
            raise WIClientError(msg)

        if ((minlat == -90.0) and (maxlat == 90.0) and (minlon == -180.0) and
                (maxlon == 180.0)):
            geoLoc = None
        else:
            geoLoc = GeoRectangle(minlat, maxlat, minlon, maxlon)

        try:
            st = Stream(net, sta, loc, cha)
            tw = TW(start, endt)
            result.extend(routes.getRoute(st, tw, ser, geoLoc, alt))
        except RoutingException:
            pass

    if not filterdefined:
        st = Stream('*', '*', '*', '*')
        tw = TW(None, None)
        geoLoc = None
        result.extend(routes.getRoute(st, tw, ser, geoLoc, alt))

    if len(result) == 0:
        raise WIContentError()
    return result


# This variable will be treated as GLOBAL by all the other functions
routes = None


def application(environ, start_response):
    # Warning is the default value
    # verboNum = getattr(logging, verbo.upper(), 30)
    # logging.info('Verbosity configured with %s' % verboNum)
    # logging.basicConfig(level=verboNum)

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    # if fname is None:
    #     raise WIClientError('Method name not recognized!')
    #     # return send_html_response(status, 'Error! ' + status, start_response)

    if len(environ['QUERY_STRING']) > 1000:
        return send_error_response("414 Request URI too large",
                                   "maximum URI length is 1000 characters",
                                   start_response)

    try:
        if environ['REQUEST_METHOD'] == 'GET':
            form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            try:
                outForm = getParam(form, ['format'], default='xml').lower()
            except Exception:
                message = "Error while parsing parameter 'format': %s" % str(form['format'])
                return send_error_response("400 Bad Request", message, start_response)

        elif environ['REQUEST_METHOD'] == 'POST':
            try:
                length = int(environ.get('CONTENT_LENGTH', '0'))
            except ValueError:
                length = 0

            # If there is a body to read
            if length:
                form = environ['wsgi.input'].read(length).decode()
            else:
                form = environ['wsgi.input'].read().decode()

            for line in form.splitlines():
                if not len(line):
                    continue

                if '=' not in line:
                    break
                k, v = line.split('=')
                if k.strip() == 'format':
                    outForm = v.strip()

        else:
            raise Exception

    except ValueError as e:
        if str(e) == "Maximum content length exceeded":
            # Add some user-friendliness (this message triggers an alert
            # box on the client)
            return send_error_response("400 Bad Request",
                                       "maximum request size exceeded",
                                       start_response)

        return send_error_response("400 Bad Request", str(e), start_response)


def main():
    uvicorn.run(
        "routing:routingws",
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        reload=True,
    )


if __name__ == "__main__":
    main()
