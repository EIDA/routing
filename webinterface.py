#!/usr/bin/env python
#
# FDSN-WS Dataselect prototype
#
# Begun by Javier Quinteros, GEOFON team, February 2014
# <javier@gfz-potsdam.de>
#
# ----------------------------------------------------------------------


"""FDSN-WS Dataselect prototype

(c) 2014 GEOFON, GFZ Potsdam

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2, or (at your option) any later
version. For more information, see http://www.gnu.org/

"""

import cgi

# JSON (since Python 2.6)
import json

# SC3 stuff
import seiscomp3.System
import seiscomp3.Config
import seiscomp3.Logging

from seiscomp import logs
from wsgicomm import *
from inventorycache import InventoryCache

# Verbosity level a la SeisComP logging.level: 1=ERROR, ... 4=DEBUG
# (global parameters, settable in wsgi file)
verbosity = 3
syslog_facility = 'local0'

# Maximum size of POST data, in bytes? Or roubles?
cgi.maxlen = 1000000

##################################################################


class WebInterface(object):
    def __init__(self, appName):
        # initialize SC3 environment
        env = seiscomp3.System.Environment_Instance()

        # set up logging
        self.__syslog = seiscomp3.Logging.SyslogOutput()
        self.__syslog.open(appName, syslog_facility)

        for (v, c) in ((1, "error"), (2, "warning"), (2, "notice"),
                       (3, "info"), (4, "debug")):
            if verbosity >= v:
                self.__syslog.subscribe(seiscomp3.Logging.getGlobalChannel(c))

        logs.debug = seiscomp3.Logging.debug
        logs.info = seiscomp3.Logging.info
        logs.notice = seiscomp3.Logging.notice
        logs.warning = seiscomp3.Logging.warning
        logs.error = seiscomp3.Logging.error

        logs.notice("Starting EIDA webinterface")

        # load SC3 config files from all standard locations (SEISCOMP_ROOT
        # must be set)
        self.__cfg = seiscomp3.Config.Config()
        env.initConfig(self.__cfg, appName, env.CS_FIRST, env.CS_LAST, True)

        # Add inventory cache here, to be accessible to all modules
        inventory = './Arclink-inventory.xml'
        self.ic = InventoryCache(inventory)

        # Add routing cache here, to be accessible to all modules
        routesFile = './routing.xml'
        self.routes = RoutingTable(routesFile)

        logs.debug(str(self))


##################################################################
#
# Initialization of variables used inside the module
#
##################################################################

wi = WebInterface(__name__)


def application(environ, start_response):
    """Main WSGI handler that processes client requests and calls
    the proper functions.

    Begun by Javier Quinteros <javier@gfz-potsdam.de>,
    GEOFON team, February 2014

    """

    # Read the URI and save the first word in fname
    #fname = environ['PATH_INFO'].split("/")[-1]
    #fname = environ['PATH_INFO'].lstrip('/').split("/")[0]
    #print "environ['PATH_INFO'].lstrip('/')", environ['PATH_INFO'].lstrip('/')

    fname = environ['PATH_INFO']

    logs.debug('fname: %s' % (fname))

    # Among others, this will filter wrong function names,
    # but also the favicon.ico request, for instance.
    if fname is None:
        return send_html_response(status, 'Error! ' + status, start_response)

    try:
        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)

    except ValueError, e:
        if str(e) == "Maximum content length exceeded":
            # Add some user-friendliness (this message triggers an alert
            # box on the client)
            return send_plain_response("400 Bad Request",
                                       "maximum request size exceeded",
                                       start_response)

        return send_plain_response("400 Bad Request", str(e), start_response)

    if form:
        for k in form.keys():
            if k in multipar:
                parameters[k] = form.getlist(k)

            else:
                parameters[k] = form.getfirst(k)

    logs.debug('parameters: %s' % (parameters))

    body = []

    # body.extend(["%s: %s" % (key, value)
    #     for key, value in environ.iteritems()])

    # status = '200 OK'
    # return send_plain_response(status, body, start_response)

    logs.debug('Calling %s' % action)

    # res_string = action(environ, parameters)
    res_string = 'OK'

    if isinstance(res_string, basestring):
        status = '200 OK'
        body = res_string
        return send_plain_response(status, body, start_response)

    elif hasattr(res_string, 'filename'):
        status = '200 OK'
        body = res_string
        return send_file_response(status, body, start_response)

    status = '200 OK'
    body = "\n".join(res_string)
    return send_plain_response(status, body, start_response)
