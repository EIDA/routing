#!/usr/bin/env python
#
# Routing WS prototype
#
# (c) 2014 Javier Quinteros, GEOFON team
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------

"""Routing Webservice for EIDA

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
import cgi
import datetime
import xml.etree.cElementTree as ET
import json
from wsgicomm import WIContentError
from wsgicomm import WIClientError
from wsgicomm import WIError
from wsgicomm import send_plain_response
from wsgicomm import send_xml_response
import logging
from utils import RequestMerge
from utils import RoutingCache
from utils import RoutingException

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

def _ConvertDictToXmlRecurse(parent, dictitem):
    assert not isinstance(dictitem, list)

    if isinstance(dictitem, dict):
        for (tag, child) in dictitem.iteritems():
            if str(tag) == '_text':
                parent.text = str(child)
            elif isinstance(child, list):
                # iterate through the array and convert
                for listchild in child:
                    elem = ET.Element(tag)
                    parent.append(elem)
                    _ConvertDictToXmlRecurse(elem, listchild)
            else:
                elem = ET.Element(tag)
                parent.append(elem)
                _ConvertDictToXmlRecurse(elem, child)
    else:
        parent.text = str(dictitem)


def ConvertDictToXml(listdict):
    """
    Converts a list with dictionaries to an XML ElementTree Element
    """

    r = ET.Element('service')
    for di in listdict:
        d = {'datacenter': di}
        roottag = d.keys()[0]
        root = ET.SubElement(r, roottag)
        _ConvertDictToXmlRecurse(root, d[roottag])
    return r


# Important to support the comma-syntax from FDSN (f.i. GE,RO,XX)
def lsNSLC(net, sta, loc, cha):
    for n in net:
        for s in sta:
            for l in loc:
                for c in cha:
                    yield (n, s, l, c)


def makeQueryGET(parameters):
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
            start = datetime.datetime.strptime(
                parameters['starttime'].value[:19].upper(),
                '%Y-%m-%dT%H:%M:%S')
        elif 'start' in parameters:
            start = datetime.datetime.strptime(
                parameters['start'].value[:19].upper(),
                '%Y-%m-%dT%H:%M:%S')
        else:
            start = None
    except:
        msg = 'Error while converting starttime parameter.'
        raise WIClientError(msg)

    try:
        if 'endtime' in parameters:
            endt = datetime.datetime.strptime(
                parameters['endtime'].value[:19].upper(),
                '%Y-%m-%dT%H:%M:%S')
        elif 'end' in parameters:
            endt = datetime.datetime.strptime(
                parameters['end'].value[:19].upper(),
                '%Y-%m-%dT%H:%M:%S')
        else:
            endt = None
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
            alt = True if parameters['alternative'].value.lower() == 'true'\
                else False
        else:
            alt = False
    except:
        alt = False

    result = RequestMerge()
    # Expand lists in parameters (f.i., cha=BHZ,HHN) and yield all possible
    # values
    for (n, s, l, c) in lsNSLC(net, sta, loc, cha):
        try:
            result.extend(routes.getRoute(n, s, l, c, start, endt, ser, alt))
        except RoutingException:
            pass

    if len(result) == 0:
        raise WIContentError('No routes have been found!')
    return result


def makeQueryPOST(postText):
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
            start = None if start in ("''", '""') else \
                datetime.datetime.strptime(start[:19].upper(),
                                           '%Y-%m-%dT%H:%M:%S')
        except:
            msg = 'Error while converting %s to datetime' % start
            raise WIClientError(msg)

        try:
            endt = None if endt in ("''", '""') else \
                datetime.datetime.strptime(endt[:19].upper(),
                                           '%Y-%m-%dT%H:%M:%S')
        except:
            msg = 'Error while converting %s to datetime' % endt
            raise WIError(msg)

        try:
            result.extend(routes.getRoute(net, sta, loc, cha,
                                          start, endt, ser, alt))
        except RoutingException:
            pass

    if len(result) == 0:
        raise WIContentError('No routes have been found!')
    return result


def applyFormat(resultRM, outFormat='xml'):
    """Apply the format specified to the RequestMerge object received.

    :rtype: str
    :returns: Transformed version of the input in the desired format
    """

    if not isinstance(resultRM, RequestMerge):
        raise Exception('applyFormat expects a RequestMerge object!')

    if outFormat == 'json':
        iterObj = json.dumps(resultRM, default=datetime.datetime.isoformat)
        return iterObj
    elif outFormat == 'get':
        iterObj = []
        for datacenter in resultRM:
            for item in datacenter['params']:
                iterObj.append(datacenter['url'] + '?' +
                               '&'.join([k + '=' + (str(item[k]) if
                                         type(item[k]) is not
                                         type(datetime.datetime.now())
                                         else item[k].isoformat()) for k in item
                                         if item[k] not in ('', '*')
                                         and k != 'priority']))
        iterObj = '\n'.join(iterObj)
        return iterObj
    elif outFormat == 'post':
        iterObj = []
        for datacenter in resultRM:
            iterObj.append(datacenter['url'])
            for item in datacenter['params']:
                item['loc'] = item['loc'] if len(item['loc']) else '--'
                iterObj.append(item['net'] + ' ' + item['sta'] + ' ' +
                               item['loc'] + ' ' + item['cha'] + ' ' +
                               item['start'] + ' ' + item['end'])
            iterObj.append('')
        iterObj = '\n'.join(iterObj)
        return iterObj
    else:
        iterObj2 = ET.tostring(ConvertDictToXml(resultRM))
        return iterObj2

# This variable will be treated as GLOBAL by all the other functions
routes = None


def application(environ, start_response):
    """Main WSGI handler that processes client requests and calls
    the proper functions.

    """

    global routes
    fname = environ['PATH_INFO']

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if fname is None:
        raise WIClientError('Method name not recognized!')
        # return send_html_response(status, 'Error! ' + status, start_response)

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
            return send_plain_response("400 Bad Request",
                                       "maximum request size exceeded",
                                       start_response)

        return send_plain_response("400 Bad Request", str(e), start_response)

    # Check whether the function called is implemented
    implementedFunctions = ['query', 'application.wadl', 'localconfig',
                            'version', 'info']

    config = configparser.RawConfigParser()
    here = os.path.dirname(__file__)
    config.read(os.path.join(here, 'routing.cfg'))
    verbo = config.get('Service', 'verbosity')
    # Warning is the default value
    verboNum = getattr(logging, verbo.upper(), 30)
    logging.basicConfig(level=verboNum)

    if routes is None:
        # Add routing cache here, to be accessible to all modules
        routesFile = os.path.join(here, 'data', 'routing.xml')
        #invFile = os.path.join(here, 'data', 'Arclink-inventory.xml')
        masterFile = os.path.join(here, 'data', 'masterTable.xml')
        #routes = RoutingCache(routesFile, masterFile, Logs(verbo))
        routes = RoutingCache(routesFile, masterFile)

    fname = environ['PATH_INFO'].split('/')[-1]
    if fname not in implementedFunctions:
        return send_plain_response("400 Bad Request",
                                   'Function "%s" not implemented.' % fname,
                                   start_response)

    if fname == 'application.wadl':
        iterObj = ''
        here = os.path.dirname(__file__)
        appWadl = os.path.join(here, 'application.wadl')
        with open(appWadl, 'r') \
                as appFile:
            iterObj = appFile.read()
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
            else:
                return send_plain_response(status, iterObj, start_response)

        except WIError as w:
            return send_plain_response(w.status, w.body, start_response)

    elif fname == 'localconfig':
        return send_xml_response('200 OK', routes.localConfig(),
                                 start_response)

    elif fname == 'version':
        text = "1.0.2"
        return send_plain_response('200 OK', text, start_response)

    elif fname == 'info':
        config = configparser.RawConfigParser()
        here = os.path.dirname(__file__)
        config.read(os.path.join(here, 'routing.cfg'))

        text = config.get('Service', 'info')
        return send_plain_response('200 OK', text, start_response)

    raise Exception('This point should have never been reached!')


def main():
    routes = RoutingCache("./routing.xml", "./masterTable.xml")


if __name__ == "__main__":
    main()
