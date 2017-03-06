#!/usr/bin/env python

"""Routing Service for EIDA

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
from routeutils.wsgicomm import send_xml_response
from routeutils.wsgicomm import send_error_response
from routeutils.utils import RequestMerge
from routeutils.utils import RoutingCache
from routeutils.utils import RoutingException
from routeutils.routing import lsNSLC
from routeutils.routing import applyFormat

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


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
                     'service', 'format',
                     'alternative']

    for param in parameters:
        if param not in allowedParams:
            msg = 'Unknown parameter: %s' % param
            raise WIClientError(msg)

    try:
        if 'network' in parameters:
            net = parameters['network'].value.upper()
        elif 'net' in parameters:
            net = parameters['net'].value.upper()
        else:
            net = '*'

        net = net.split(',')
    except:
        net = ['*']

    try:
        if 'station' in parameters:
            sta = parameters['station'].value.upper()
        elif 'sta' in parameters:
            sta = parameters['sta'].value.upper()
        else:
            sta = '*'

        sta = sta.split(',')
    except:
        sta = ['*']

    try:
        if 'location' in parameters:
            loc = parameters['location'].value.upper()
        elif 'loc' in parameters:
            loc = parameters['loc'].value.upper()
        else:
            loc = '*'

        loc = loc.split(',')
    except:
        loc = ['*']

    try:
        if 'channel' in parameters:
            cha = parameters['channel'].value.upper()
        elif 'cha' in parameters:
            cha = parameters['cha'].value.upper()
        else:
            cha = '*'

        cha = cha.split(',')
    except:
        cha = ['*']

    try:
        if 'starttime' in parameters:
            start = parameters['starttime'].value.upper()
        elif 'start' in parameters:
            start = parameters['start'].value.upper()
        else:
            start = None

        if start is not None:
            startParts = start.replace('-', ' ').replace('T', ' ')
            startParts = startParts.replace(':', ' ').replace('.', ' ')
            startParts = startParts.replace('Z', '').split()
            start = datetime.datetime(*map(int, startParts))
        # if 'starttime' in parameters:
        #     start = datetime.datetime.strptime(
        #         parameters['starttime'].value[:19].upper(),
        #         '%Y-%m-%dT%H:%M:%S')
        # elif 'start' in parameters:
        #     start = datetime.datetime.strptime(
        #         parameters['start'].value[:19].upper(),
        #         '%Y-%m-%dT%H:%M:%S')
        # else:
        #     start = None
    except:
        msg = 'Error while converting starttime parameter.'
        raise WIClientError(msg)

    try:
        if 'endtime' in parameters:
            endt = parameters['endtime'].value.upper()
        elif 'end' in parameters:
            endt = parameters['end'].value.upper()
        else:
            endt = None

        if endt is not None:
            endParts = endt.replace('-', ' ').replace('T', ' ')
            endParts = endParts.replace(':', ' ').replace('.', ' ')
            endParts = endParts.replace('Z', '').split()
            endt = datetime.datetime(*map(int, endParts))
        # if 'endtime' in parameters:
        #     endt = datetime.datetime.strptime(
        #         parameters['endtime'].value[:19].upper(),
        #         '%Y-%m-%dT%H:%M:%S')
        # elif 'end' in parameters:
        #     endt = datetime.datetime.strptime(
        #         parameters['end'].value[:19].upper(),
        #         '%Y-%m-%dT%H:%M:%S')
        # else:
        #     endt = None
    except:
        msg = 'Error while converting endtime parameter.'
        raise WIClientError(msg)

    try:
        if 'service' in parameters:
            ser = parameters['service'].value.lower()
        else:
            ser = 'dataselect'
    except:
        ser = 'dataselect'

    try:
        if 'alternative' in parameters:
            if parameters['alternative'].value.lower() == 'true':
                alt = True
            elif parameters['alternative'].value.lower() == 'false':
                alt = False
            else:
                msg = 'Wrong value passed in parameter "alternative"'
                raise WIClientError(msg)
        else:
            alt = False
    except WIClientError:
        raise
    except:
        alt = False

    try:
        if 'format' in parameters:
            form = parameters['format'].value.lower()
        else:
            form = 'xml'
    except:
        form = 'xml'

    if ((alt) and (form == 'get')):
        msg = 'alternative=true and format=get are incompatible parameters'
        raise WIClientError(msg)

    if ((start is not None) and (endt is not None) and (start > endt)):
        msg = 'Start datetime cannot be greater than end datetime'
        raise WIClientError(msg)

    result = RequestMerge()
    # Expand lists in parameters (f.i., cha=BHZ,HHN) and yield all possible
    # values
    for (n, s, l, c) in lsNSLC(net, sta, loc, cha):
        try:
            result.extend(routes.getRoute(n, s, l, c, start, endt, ser, alt))
        except RoutingException:
            pass

    if len(result) == 0:
        raise WIContentError()
    return result


def makeQueryPOST(postText):
    """Process a request made via a POST method."""
    global routes

    # This are the parameters accepted appart from N.S.L.C
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
            startParts = start.replace('-', ' ').replace('T', ' ')
            startParts = startParts.replace(':', ' ').replace('.', ' ')
            startParts = startParts.replace('Z', '').split()
            start = datetime.datetime(*map(int, startParts))
            # start = None if start in ("''", '""') else \
            #     datetime.datetime.strptime(start[:19].upper(),
            #                                '%Y-%m-%dT%H:%M:%S')
        except:
            msg = 'Error while converting %s to datetime' % start
            raise WIClientError(msg)

        try:
            endParts = endt.replace('-', ' ').replace('T', ' ')
            endParts = endParts.replace(':', ' ').replace('.', ' ')
            endParts = endParts.replace('Z', '').split()
            endt = datetime.datetime(*map(int, endParts))
            # endt = None if endt in ("''", '""') else \
            #     datetime.datetime.strptime(endt[:19].upper(),
            #                                '%Y-%m-%dT%H:%M:%S')
        except:
            msg = 'Error while converting %s to datetime' % endt
            raise WIError(msg)

        try:
            result.extend(routes.getRoute(net, sta, loc, cha,
                                          start, endt, ser, alt))
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
            if length != 0:
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
                            'version', 'info']

    config = configparser.RawConfigParser()
    here = os.path.dirname(__file__)
    config.read(os.path.join(here, 'routing.cfg'))
    verbo = config.get('Service', 'verbosity')
    baseURL = config.get('Service', 'baseURL')
    # Warning is the default value
    verboNum = getattr(logging, verbo.upper(), 30)
    logging.info('Verbosity configured with %s' % verboNum)
    logging.basicConfig(level=verboNum)

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

    if fname == 'application.wadl':
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
        text = "1.0.4"
        return send_plain_response('200 OK', text, start_response)

    elif fname == 'info':
        config = configparser.RawConfigParser()
        here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))

        text = config.get('Service', 'info')
        return send_plain_response('200 OK', text, start_response)

    raise Exception('This point should have never been reached!')


def main():
    """Main function in case of calling the script from the command line."""
    global routes
    routes = RoutingCache("./routing.xml", "./masterTable.xml")


if __name__ == "__main__":
    main()
