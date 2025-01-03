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

import os
import cgi
import datetime
import logging
import configparser
import json
from http import HTTPStatus
from routeutils.wsgicomm import WIContentError
from routeutils.wsgicomm import WIClientError
from routeutils.wsgicomm import WIError
from routeutils.wsgicomm import send_plain_response
from routeutils.wsgicomm import send_json_response
from routeutils.wsgicomm import send_html_response
from routeutils.wsgicomm import send_xml_response
from routeutils.wsgicomm import send_error_response
from routeutils.utils import Stream
from routeutils.utils import TW
from routeutils.utils import GeoRectangle
from routeutils.utils import RequestMerge
from routeutils.utils import RoutingCache
from routeutils.utils import RoutingException
from routeutils.utils import str2date
from routeutils.routing import lsNSLC
from routeutils.routing import applyFormat
from typing import Union
from typing import List


def getParam(parameters: Union[cgi.FieldStorage, dict], names: Union[list, set],
             default: Union[str, None], csv: bool = False) -> Union[str, List[str], None]:
    """Read a parameter and return its value or a default value in case it is not found.

    The csv parameter is used to split the value in case of multiple values separated by commas. This means
    that the result will be a string if csv is False, and a list of string(s) if csv is True.
    """
    for n in names:
        if n in parameters:
            if isinstance(parameters[n], list):
                raise Exception('Parameter(s) %s returned a list instead of a value. Multiple input?' % names)
            result = parameters[n].value.upper()
            break
    else:
        result = default

    # WARNING This converts the result from a string to a list with a string(s) if "cvs" is True
    if csv:
        result = result.split(',')

    return result


def makeQueryGET(parameters: Union[cgi.FieldStorage, dict]) -> RequestMerge:
    """Process a request made via a GET method."""
    global routes

    # List all the accepted parameters
    allowedParams = ['net', 'network',
                     'sta', 'station',
                     'loc', 'location',
                     'cha', 'channel',
                     'start', 'starttime',
                     'end', 'endtime',
                     'minlat', 'minlatitude',
                     'maxlat', 'maxlatitude',
                     'minlon', 'minlongitude',
                     'maxlon', 'maxlongitude',
                     'service', 'format',
                     'alternative', 'nodata']

    for param in parameters:
        if param not in allowedParams:
            msg = 'Unknown parameter: %s' % param
            raise WIClientError(msg)

    try:
        # If CSV is True the result will be a list!
        net = getParam(parameters, ['net', 'network'], '*', csv=True)
        sta = getParam(parameters, ['sta', 'station'], '*', csv=True)
        loc = getParam(parameters, ['loc', 'location'], '*', csv=True)
        cha = getParam(parameters, ['cha', 'channel'], '*', csv=True)
        # Here the result will be a string
        start = getParam(parameters, ['start', 'starttime'], None)
    except Exception as e:
        raise WIClientError(str(e))

    try:
        if start is not None:
            start = str2date(start)
    except Exception:
        msg = 'Error while converting starttime parameter.'
        raise WIClientError(msg)

    # The result will be a string (not a list)
    endt = getParam(parameters, ['end', 'endtime'], None)
    try:
        if endt is not None:
            endt = str2date(endt)
    except Exception:
        msg = 'Error while converting endtime parameter.'
        raise WIClientError(msg)

    try:
        minlat = float(getParam(parameters, ['minlat', 'minlatitude'],
                                '-90.0'))
    except Exception:
        msg = 'Error while converting the minlatitude parameter.'
        raise WIClientError(msg)

    try:
        maxlat = float(getParam(parameters, ['maxlat', 'maxlatitude'],
                                '90.0'))
    except Exception:
        msg = 'Error while converting the maxlatitude parameter.'
        raise WIClientError(msg)

    try:
        minlon = float(getParam(parameters, ['minlon', 'minlongitude'],
                                '-180.0'))
    except Exception:
        msg = 'Error while converting the minlongitude parameter.'
        raise WIClientError(msg)

    try:
        maxlon = float(getParam(parameters, ['maxlon', 'maxlongitude'],
                                '180.0'))
    except Exception:
        msg = 'Error while converting the maxlongitude parameter.'
        raise WIClientError(msg)

    # These two results will be strings
    ser = getParam(parameters, ['service'], 'dataselect').lower()
    aux = getParam(parameters, ['alternative'], 'false').lower()
    if aux == 'true':
        alt = True
    elif aux == 'false':
        alt = False
    else:
        msg = 'Wrong value passed in parameter "alternative"'
        raise WIClientError(msg)

    # form will be a string
    form = getParam(parameters, ['format'], 'xml').lower()

    if alt and (form == 'get'):
        msg = 'alternative=true and format=get are incompatible parameters'
        raise WIClientError(msg)

    # print start, type(start), endt, type(endt), (start > endt)
    if (start is not None) and (endt is not None) and (start > endt):
        msg = 'Start datetime cannot be greater than end datetime'
        raise WIClientError(msg)

    if ((minlat == -90.0) and (maxlat == 90.0) and (minlon == -180.0) and
            (maxlon == 180.0)):
        geoLoc = None
    else:
        geoLoc = GeoRectangle(minlat, maxlat, minlon, maxlon)

    result = RequestMerge()
    # Expand lists in parameters (f.i., cha=BHZ,HHN) and yield all possible
    # values
    for (n, s, l, c) in lsNSLC(net, sta, loc, cha):
        try:
            st = Stream(n, s, l, c)
            tw = TW(start, endt)
            result.extend(routes.getRoute(st, tw, ser, geoLoc, alt))
        except RoutingException:
            pass

    if len(result) == 0:
        raise WIContentError()
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
    """Main WSGI handler. Process requests and calls proper functions."""
    global routes
    fname = environ['PATH_INFO']

    config = configparser.RawConfigParser()
    here = os.path.dirname(__file__)
    config.read(os.path.join(here, 'routing.cfg'))
    verbo = config.get('Service', 'verbosity')
    baseURL = config.get('Service', 'baseURL')
    # Warning is the default value
    verboNum = getattr(logging, verbo.upper(), 30)
    logging.info('Verbosity configured with %s' % verboNum)
    logging.basicConfig(level=verboNum)

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if fname is None:
        raise WIClientError('Method name not recognized!')
        # return send_html_response(status, 'Error! ' + status, start_response)

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

    # Check whether the function called is implemented
    implementedFunctions = ['query', 'application.wadl', 'localconfig',
                            'globalconfig', 'version', 'info', '',
                            'virtualnets', 'endpoints', 'dc']

    if routes is None:
        # Add routing cache here, to be accessible to all modules
        routesFile = os.path.join(here, 'data', 'routing.xml')
        configFile = os.path.join(here, 'routing.cfg')
        routes = RoutingCache(routesFile, configFile)

    fname = environ['PATH_INFO'].split('/')[-1]
    if fname not in implementedFunctions:
        return send_error_response("400 Bad Request",
                                   'Function "%s" not implemented.' % fname,
                                   start_response)

    if fname == '':
        # here = os.path.dirname(__file__)
        helpFile = os.path.join(here, 'help.html')
        with open(helpFile, 'r') as helpHandle:
            iterObj = helpHandle.read()
            status = '200 OK'
            return send_html_response(status, iterObj, start_response)

    elif fname == 'application.wadl':
        # here = os.path.dirname(__file__)
        appWadl = os.path.join(here, 'application.wadl')
        with open(appWadl, 'r') \
                as appFile:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            iterObj = appFile.read() % (baseURL, tomorrow)
            status = '200 OK'
            return send_xml_response(status, iterObj, start_response)

    elif fname == 'query':
        makeQuery = globals()['makeQuery%s' % environ['REQUEST_METHOD']]
        try:
            iterObj = makeQuery(form)

            iterObj = applyFormat(iterObj, outForm)

            status = '200 OK'
            if outForm == 'xml':
                return send_xml_response(status, iterObj, start_response)
            elif outForm == 'json':
                return send_json_response(status, iterObj, start_response)
            else:
                return send_plain_response(status, iterObj, start_response)

        except WIError as w:
            if isinstance(w, WIContentError) and 'nodata' in form:
                retcode = getParam(form, ['nodata'], '204')
                retstatus = '%s %s' % (retcode, HTTPStatus(int(retcode)).phrase)
            else:
                retstatus = w.status
            return send_error_response(retstatus, w.body, start_response)

    elif fname == 'dc':
        try:
            with open(os.path.join(here, 'data', 'routing.json')) as fin:
                dc = json.load(fin)
        except Exception:
            dc = dict()

        return send_json_response('200 OK', dc, start_response)

    elif fname == 'endpoints':
        result = routes.endpoints()
        return send_plain_response('200 OK', result, start_response)

    elif fname == 'localconfig':
        result = routes.localConfig()
        if outForm == 'xml':
            return send_xml_response('200 OK', result,
                                     start_response)

    elif fname == 'globalconfig':
        result = routes.globalConfig()
        if outForm == 'fdsn':
            return send_json_response('200 OK', result,
                                      start_response)

        # Only FDSN format is supported for the time being
        text = 'Only format=FDSN is supported'
        return send_error_response("400 Bad Request", text, start_response)

    elif fname == 'virtualnets':
        result = routes.virtualNets()
        return send_json_response('200 OK', result,
                                  start_response)

    elif fname == 'version':
        text = "1.2.3"
        return send_plain_response('200 OK', text, start_response)

    elif fname == 'info':
        config = configparser.RawConfigParser()
        # here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))

        text = config.get('Service', 'info')
        return send_plain_response('200 OK', text, start_response)

    raise Exception('This point should have never been reached!')
