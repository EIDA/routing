#!/usr/bin/env python

"""Functions and resources to communicate via a WSGI module

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

import sys


class Logs(object):
    """Given a log level and a stream, redirect the output to the proper place.

    :Platform: Linux

    """

    def __init__(self, level=2, outstr=sys.stdout):
        """Constructor of Logs class."""
        self.setLevel(level)
        self.outstr = outstr

    def setLevel(self, level):
        """Set the level of the log.

        :param level: Log level (1: Error, 2: Warning, 3: Info, 4: Debug)
        :type level: int

        """
        # Remap the functions in agreement with the output level
        # Default values are the following
        self.error = self.__pass
        self.warning = self.__pass
        self.info = self.__pass
        self.debug = self.__pass

        if level >= 1:
            self.error = self.__write
        if level >= 2:
            self.warning = self.__write
        if level >= 3:
            self.info = self.__write
        if level >= 4:
            self.debug = self.__write

    def __write(self, msg):
        self.outstr.write(msg)
        self.outstr.flush()

    def __pass(self, msg):
        pass


##################################################################
#
# Exceptions to be caught (usually) by the application handler
#
##################################################################


class PlsRedirect(Exception):
    """Exception to signal that the web client must be redirected to a URL.

    The constructor of the class receives a string, which is the
    URL where the web browser is going to be redirected.

    """

    def __init__(self, url):
        """Constructor for PlsRedirect."""
        self.url = url

    def __str__(self):
        """Show the URL of the redirection in the str representation."""
        return repr(self.url)


class WIError(Exception):
    """Exception to signal that an error occurred.

    :platform: Linux

    """

    def __init__(self, status, body, verbosity=1):
        """Constructor of the WIError class.

        :param status: HTTP code number and short description associated to it
        :type status: str
        :param body: plain text content to display to the client
        :type body: str
        :param verbosity: 0 = silent, 4 = debug
        :type verbosity: int

        """
        self.status = status
        self.body = body
        self.verbosity = verbosity

    def __str__(self):
        """Show the error code and body of the Exception."""
        return repr(self.status) + ': ' + repr(self.body)


class WIURIError(WIError):
    """Exception to signal that the URI is beyond the allowed limit (414).

    :platform: Linux

    """

    def __init__(self, *args, **kwargs):
        """Constructor of WIURIError.

        If some parameter is given it will be passed to WIError as body.

        """
        WIError.__init__(self, "414 Request URI too large", *args, **kwargs)


class WIContentError(WIError):
    """Exception to signal that no content was found (204).

    :platform: Linux

    """

    def __init__(self, *args, **kwargs):
        """Constructor of WIContentError.

        If some parameter is given it will be passed to WIError as body.

        """
        WIError.__init__(self, "204 No Content", '', *args, **kwargs)


class WIClientError(WIError):
    """Exception to signal that an invalid request was received (400).

    :platform: Linux

    """

    def __init__(self, *args, **kwargs):
        """Constructor of WIClientError.

        If some parameter is given it will be passed to WIError as body.

        """
        WIError.__init__(self, "400 Bad Request", *args, **kwargs)


class WIInternalError(WIError):
    """Exception to signal that an internal server error occurred (500).

    :platform: Linux

    """

    def __init__(self, *args, **kwargs):
        """Constructor of WIInternalError.

        If some parameter is given it will be passed to WIError as body.

        """
        WIError.__init__(self, "500 Internal Server Error", *args, **kwargs)


class WIServiceError(WIError):
    """Exception to signal that the service is unavailable (503).

    :platform: Linux

    """

    def __init__(self, *args, **kwargs):
        """Constructor of WIServiceError.

        If some parameter is given it will be passed to WIError as body.

        """
        WIError.__init__(self, "503 Service Unavailable", *args, **kwargs)


##################################################################
#
# Functions to send a response to the client
#
##################################################################

def redirect_page(url, start_response):
    """Tell the web client through the WSGI module to redirect to a URL.

    :platform: Linux

    """
    response_headers = [('Location', url)]
    start_response('301 Moved Permanently', response_headers)
    return ''


def send_html_response(status, body, start_response):
    """Send an HTML response in WSGI style.

    :platform: Linux

    """
    response_headers = [('Content-Type', 'text/html; charset=UTF-8'),
                        ('Content-Length', str(len(body)))]
    start_response(status, response_headers)
    return [body]


def send_xml_response(status, body, start_response):
    """Send an XML response in WSGI style.

    :platform: Linux

    """
    response_headers = [('Content-Type', 'text/xml; charset=UTF-8'),
                        ('Content-Length', str(len(body)))]
    start_response(status, response_headers)
    return [body]


def send_plain_response(status, body, start_response):
    """Send a plain response in WSGI style.

    :platform: Linux

    """
    response_headers = [('Content-Type', 'text/plain'),
                        ('Content-Length', str(len(body)))]
    start_response(status, response_headers)
    return [body]


def send_nobody_response(status, start_response):
    """Send a plain response without body in WSGI style.

    :platform: Linux

    """
    response_headers = [('Content-Length', 0)]
    start_response(status, response_headers)
    return []


def send_error_response(status, body, start_response):
    """Send a plain response in WSGI style.

    :platform: Linux

    """
    response_headers = [('Content-Type', 'text/plain')]
    # print response_headers
    # print status
    # print sys.exc_info()
    start_response(status, response_headers, sys.exc_info())
    return [body]


def send_file_response(status, body, start_response):
    """Send a file (or file-like) object.

    Caller must set the filename, size and content_type attributes of body.

    :platform: Linux

    """
    response_headers = [('Content-Type', body.content_type),
                        ('Content-Length', str(body.size)),
                        ('Content-Disposition', 'attachment; filename=%s' %
                         (body.filename))]
    start_response(status, response_headers)
    return body


def send_dynamicfile_response(status, body, start_response):
    """Send a file (or file-like) object.

    Caller must set the filename, size and content_type attributes of body.

    :platform: Linux

    """
    # Cycle through the iterator in order to retrieve one chunck at a time
    loop = 0
    for data in body:
        if loop == 0:
            # The first thing to do is to send the headers.
            # This needs to be done here so that we are sure that there is
            # ACTUALLY data to send

            # Content-length cannot be set because the file size is unknown
            response_headers = [('Content-Type', body.content_type),
                                ('Content-Disposition',
                                 'attachment; filename=%s' % (body.filename))]
            start_response(status, response_headers)

        # Increment the loop count
        loop += 1
        # and send data
        yield data

    if loop == 0:
        send_nobody_response('204 No Content', start_response)
