"""Routing Service for EIDA.

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
import cgi
import datetime
import logging
from routeutils.wsgicomm import WIContentError
from routeutils.wsgicomm import WIClientError
from routeutils.wsgicomm import WIError
from routeutils.wsgicomm import send_plain_response
from routeutils.wsgicomm import send_html_response
from routeutils.wsgicomm import send_xml_response
from routeutils.wsgicomm import send_error_response
from routeutils.utils import Stream
from routeutils.utils import TW
from routeutils.utils import geoRectangle
from routeutils.utils import RequestMerge
from routeutils.utils import RoutingCache
from routeutils.utils import RoutingException
from routeutils.utils import str2date
from routeutils.routing import lsNSLC
from routeutils.routing import applyFormat

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


def getParam(parameters, names, default, csv=False):
    """Read a parameter and return its value or a default value."""
    try:
        for n in names:
            if n in parameters:
                result = parameters[n].value.upper()
                break
        else:
            result = default

        if csv:
            result = result.split(',')
    except:
        result = [default] if csv else default

    return result


def makeQueryGET(parameters):
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
                     'alternative']

    for param in parameters:
        if param not in allowedParams:
            msg = 'Unknown parameter: %s' % param
            raise WIClientError(msg)

    net = getParam(parameters, ['net', 'network'], '*', csv=True)
    sta = getParam(parameters, ['sta', 'station'], '*', csv=True)
    loc = getParam(parameters, ['loc', 'location'], '*', csv=True)
    cha = getParam(parameters, ['cha', 'channel'], '*', csv=True)
    start = getParam(parameters, ['start', 'starttime'], None)
    try:
        if start is not None:
            start = str2date(start)
    except:
        msg = 'Error while converting starttime parameter.'
        raise WIClientError(msg)

    endt = getParam(parameters, ['end', 'endtime'], None)
    try:
        if endt is not None:
            endt = str2date(endt)
    except:
        msg = 'Error while converting endtime parameter.'
        raise WIClientError(msg)

    try:
        minlat = float(getParam(parameters, ['minlat', 'minlatitude'],
                                '-90.0'))
    except:
        msg = 'Error while converting the minlatitude parameter.'
        raise WIClientError(msg)

    try:
        maxlat = float(getParam(parameters, ['maxlat', 'maxlatitude'],
                                '90.0'))
    except:
        msg = 'Error while converting the maxlatitude parameter.'
        raise WIClientError(msg)

    try:
        minlon = float(getParam(parameters, ['minlon', 'minlongitude'],
                                '-180.0'))
    except:
        msg = 'Error while converting the minlongitude parameter.'
        raise WIClientError(msg)

    try:
        maxlon = float(getParam(parameters, ['maxlon', 'maxlongitude'],
                                '180.0'))
    except:
        msg = 'Error while converting the maxlongitude parameter.'
        raise WIClientError(msg)

    ser = getParam(parameters, ['service'], 'dataselect').lower()
    aux = getParam(parameters, ['alternative'], 'false').lower()
    if aux == 'true':
        alt = True
    elif aux == 'false':
        alt = False
    else:
        msg = 'Wrong value passed in parameter "alternative"'
        raise WIClientError(msg)

    form = getParam(parameters, ['format'], 'xml').lower()

    if ((alt) and (form == 'get')):
        msg = 'alternative=true and format=get are incompatible parameters'
        raise WIClientError(msg)

    # print start, type(start), endt, type(endt), (start > endt)
    if ((start is not None) and (endt is not None) and (start > endt)):
        msg = 'Start datetime cannot be greater than end datetime'
        raise WIClientError(msg)

    if ((minlat == -90.0) and (maxlat == 90.0) and (minlon == -180.0) and
            (maxlon == 180.0)):
        geoLoc = None
    else:
        geoLoc = geoRectangle(minlat, maxlat, minlon, maxlon)

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


def makeQueryPOST(postText):
    """Process a request made via a POST method."""
    global routes

    # These are the parameters accepted appart from N.S.L.C
    extraParams = ['format', 'service', 'alternative']

    # Defualt values
    ser = 'dataselect'
    alt = False

    result = RequestMerge()
    # Check if we are still processing the header of the POST body. This has a
    # format like key=value, one per line.
    inHeader = True

    for line in postText.splitlines():
        if not len(line):
            continue

        if (inHeader and ('=' not in line)):
            inHeader = False

        if inHeader:
            try:
                key, value = line.split('=')
                key = key.strip()
                value = value.strip()
            except:
                msg = 'Wrong format detected while processing: %s' % line
                raise WIClientError(msg)

            if key not in extraParams:
                msg = 'Unknown parameter "%s"' % key
                raise WIClientError(msg)

            if key == 'service':
                ser = value
            elif key == 'alternative':
                alt = True if value.lower() == 'true' else False

            continue

        # I'm already in the main part of the POST body, where the streams are
        # specified
        net, sta, loc, cha, start, endt = line.split()
        net = net.upper()
        sta = sta.upper()
        loc = loc.upper()
        try:
            start = str2date(start)
        except:
            msg = 'Error while converting %s to datetime' % start
            raise WIClientError(msg)

        try:
            endt = str2date(endt)
        except:
            msg = 'Error while converting %s to datetime' % endt
            raise WIError(msg)

        try:
            st = Stream(net, sta, loc, cha)
            tw = TW(start, endt)
            result.extend(routes.getRoute(st, tw, ser, None, alt))
        except RoutingException:
            pass

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
        outForm = 'xml'

        if environ['REQUEST_METHOD'] == 'GET':
            form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
            if 'format' in form:
                outForm = form['format'].value.lower()
        elif environ['REQUEST_METHOD'] == 'POST':
            form = ''
            try:
                length = int(environ.get('CONTENT_LENGTH', '0'))
            except ValueError:
                length = 0

            # If there is a body to read
            if length:
                form = environ['wsgi.input'].read(length)
            else:
                form = environ['wsgi.input'].read()

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
                            'version', 'info', '']

    if routes is None:
        # Add routing cache here, to be accessible to all modules
        routesFile = os.path.join(here, 'data', 'routing.xml')
        masterFile = os.path.join(here, 'data', 'masterTable.xml')
        configFile = os.path.join(here, 'routing.cfg')
        routes = RoutingCache(routesFile, masterFile, configFile)

    fname = environ['PATH_INFO'].split('/')[-1]
    if fname not in implementedFunctions:
        return send_error_response("400 Bad Request",
                                   'Function "%s" not implemented.' % fname,
                                   start_response)


    if fname == '':
        iterObj = ''
        here = os.path.dirname(__file__)
        helpFile = os.path.join(here, 'help.html')
        with open(helpFile, 'r') as helpHandle:
            iterObj = helpHandle.read()
            status = '200 OK'
            return send_html_response(status, iterObj, start_response)

    elif fname == 'application.wadl':
        iterObj = ''
        here = os.path.dirname(__file__)
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

            # print iterObj
            iterObj = applyFormat(iterObj, outForm)

            status = '200 OK'
            if outForm == 'xml':
                return send_xml_response(status, iterObj, start_response)
            else:
                return send_plain_response(status, iterObj, start_response)

        except WIError as w:
            return send_error_response(w.status, w.body, start_response)

    elif fname == 'localconfig':
        return send_xml_response('200 OK', routes.localConfig(),
                                 start_response)

    elif fname == 'version':
        text = "1.1.1"
        return send_plain_response('200 OK', text, start_response)

    elif fname == 'info':
        config = configparser.RawConfigParser()
        here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))

        text = config.get('Service', 'info')
        return send_plain_response('200 OK', text, start_response)

    raise Exception('This point should have never been reached!')
