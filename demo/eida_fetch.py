#!/usr/bin/env python

import sys
import time
import shutil
import optparse
import urlparse
import urllib
import urllib2
import cookielib
import tempfile
import threading
import Queue

VERSION = "1.0 (2014.290)"

class Error(Exception):
    pass

class URL(object):
    routing_params = set(('net', 'network',
                          'sta', 'station',
                          'loc', 'location',
                          'cha', 'channel',
                          'start', 'starttime',
                          'end', 'endtime',
                          'service', 'format',
                          'alternative'))

    def __init__(self, url):
        self.__url = urlparse.urlparse(url)

    def auth(self):
        u = list(self.__url)

        u[0] = 'https'
        u[2] = u[2].rsplit('/', 1)[0] + '/auth'
        u[4] = ''

        return urlparse.urlunparse(u)

    def query(self, ssl=False, **kw):
        u = list(self.__url)

        if ssl:
            u[0] = 'https'

        if kw:
            q = dict((p, v) for (p, v) in urlparse.parse_qs(u[4]).items() if p in URL.routing_params)
            q.update(kw)
            u[4] = urllib.urlencode(q, True)

        return urlparse.urlunparse(u)

    def target_params(self):
        return [(p, v[0]) for (p, v) in urlparse.parse_qs(self.__url[4]).items() if p not in URL.routing_params]

def msg(verb, s):
    if verb: print >>sys.stderr, s

def retry(urlopen, url, data, timeout, count, wait, verb):
    n = 0

    while True:
        if n >= count:
            return urlopen(url, data, timeout)

        try:
            n += 1

            fd = urlopen(url, data, timeout)

            if fd.getcode() == 200 or fd.getcode() == 204:
                return fd

            msg(verb, "retrying %s (%d) after %d seconds due to HTTP status code %d" % (url, n, wait, fd.getcode()))
            time.sleep(wait)

        except urllib2.URLError as e:
            msg(verb, "retrying %s (%d) after %d seconds due to %s" % (url, n, wait, str(e)))
            time.sleep(wait)

def fetch(url, authdata, postdata, dest, lock, timeout, retry_count, retry_wait, finished, verb):
    try:
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        if authdata:
            auth_url = url.auth()
            query_url = url.query(True)

            msg(verb, "authenticating at %s" % auth_url)

            try:
                fd = retry(opener.open, auth_url, authdata, timeout, retry_count, retry_wait, verb)

                try:
                    if fd.getcode() == 200 or fd.getcode() == 204:
                        msg(verb, "authentication at %s successful" % auth_url)

                    else:
                        msg(True, "authentication at %s failed with HTTP status code %d" % (auth_url, fd.getcode()))

                finally:
                    fd.close()

            except urllib2.URLError as e:
                msg(True, "authentication at %s failed: %s" % (auth_url, str(e)))

        else:
            query_url = url.query(False)

        msg(verb, "getting data from %s" % query_url)

        try:
            fd = retry(opener.open, query_url, postdata, timeout, retry_count, retry_wait, verb)

            try:
                if fd.getcode() == 204:
                    msg(verb, "received no data from %s" % query_url)

                elif fd.getcode() != 200:
                    msg(True, "getting data from %s failed with HTTP status code %d" % fd.getcode())

                else:
                    size = 0

                    content_type = fd.info().getheader('Content-Type')

                    if content_type == "application/vnd.fdsn.mseed":
                        while True:
                            buf = fd.read(4096)
                            if not buf: break
                            with lock: dest.write(buf)
                            size += len(buf)

                        msg(verb, "got %d bytes from %s" % (size, query_url))

                    elif content_type == "application/xml":
                        with tempfile.TemporaryFile() as tmpfd:
                            while True:
                                buf = fd.read(4096)
                                if not buf: break
                                tmpfd.write(buf)
                                size += len(buf)

                            msg(verb, "got %d bytes from %s" % (size, query_url))

                            tmpfd.seek(0)
                            with lock: shutil.copyfileobj(tmpfd, dest)

                    else:
                        msg(True, "getting data from %s failed: unsupported content type '%s'" % (query_url, content_type))

            finally:
                fd.close()

        except urllib2.URLError as e:
            msg(True, "getting data from %s failed: %s" % (query_url, str(e)))

    finally:
        finished.put(threading.current_thread())

def route(url, authdata, postdata, dest, lock, timeout, retry_count, retry_wait, maxthreads, verb):
    threads = []
    running = 0
    finished = Queue.Queue()
    query_url = url.query(format='post')

    msg(verb, "getting routes from %s" % query_url)

    try:
        fd = retry(urllib2.urlopen, query_url, postdata, timeout, retry_count, retry_wait, verb)

        try:
            if fd.getcode() == 204:
                raise Error("received no routes from %s" % query_url)

            elif fd.getcode() != 200:
                raise Error("getting routes from %s failed with code %d" % (query_url, fd.getcode()))

            else:
                url1 = None
                postlines = []

                while True:
                    line = fd.readline()

                    if not url1:
                        url1 = URL(line.strip())

                    elif not line.strip():
                        if url1 and postlines:
                            postdata1 = ''.join((p + '=' + v + '\n') for (p, v) in url.target_params()) + ''.join(postlines)
                            threads.append(threading.Thread(target=fetch, args=(url1, authdata, postdata1,
                                dest, lock, timeout, retry_count, retry_wait, finished, verb)))

                            url1 = None
                            postlines = []

                        if not line:
                            break

                    else:
                        postlines.append(line)

        finally:
            fd.close()

    except urllib2.URLError as e:
        raise Error("getting routes from %s failed: %s" % (query_url, str(e)))

    for t in threads:
        if running >= maxthreads:
            thr = finished.get(True)
            thr.join()
            running -= 1

        t.start()
        running += 1

    while running:
        thr = finished.get(True)
        thr.join()
        running -= 1

def main():
    qp = {}

    def add_qp(option, opt_str, value, parser):
        if option.dest == 'query':
            try:
                (p, v) = value.split('=', 1)
                qp[p] = v

            except ValueError as e:
                raise optparse.OptionValueError("%s expects parameter=value" % opt_str)

        else:
            qp[option.dest] = value

    parser = optparse.OptionParser(usage="Usage: %prog [-h|--help] [OPTIONS]", version="%prog v" + VERSION)

    parser.set_defaults(url = "http://geofon.gfz-potsdam.de/eidaws/routing/1/",
                        timeout = 600,
                        retries = 10,
                        retry_wait = 60,
                        threads = 5)

    parser.add_option("-v", "--verbose", action="store_true", default=False,
        help="verbose mode")

    parser.add_option("-u", "--url", type="string",
        help="URL of routing service (default %default)")

    parser.add_option("-y", "--service", type="string", action="callback", callback=add_qp,
        help="target service (default dataselect)")

    parser.add_option("-N", "--network", type="string", action="callback", callback=add_qp,
        help="network code or pattern")

    parser.add_option("-S", "--station", type="string", action="callback", callback=add_qp,
        help="station code or pattern")

    parser.add_option("-L", "--location", type="string", action="callback", callback=add_qp,
        help="location code or pattern")

    parser.add_option("-C", "--channel", type="string", action="callback", callback=add_qp,
        help="channel code or pattern")

    parser.add_option("-s", "--starttime", type="string", action="callback", callback=add_qp,
        help="start time")

    parser.add_option("-e", "--endtime", type="string", action="callback", callback=add_qp,
        help="end time")

    parser.add_option("-q", "--query", type="string", action="callback", callback=add_qp,
        help="additional query parameter", metavar="PARAMETER=VALUE")

    parser.add_option("-t", "--timeout", type="int",
        help="request timeout in seconds (default %default)")

    parser.add_option("-r", "--retries", type="int",
        help="number of retries (default %default)")

    parser.add_option("-w", "--retry-wait", type="int",
        help="seconds to wait before each retry (default %default)")

    parser.add_option("-n", "--threads", type="int",
        help="maximum number of download threads (default %default)")

    parser.add_option("-a", "--auth-file", type="string",
        help="auth file (secure mode)")

    parser.add_option("-p", "--post-file", type="string",
        help="data file for POST request")

    parser.add_option("-o", "--output-file", type="string",
        help="file where downloaded data is written")

    (options, args) = parser.parse_args()

    if args:
        parser.print_usage()
        return 1

    u = urlparse.urlparse(options.url)
    pseudourl = URL(urlparse.urlunparse((u.scheme, u.netloc, u.path.rstrip('query').rstrip('/') + '/query', '',
        urllib.urlencode(qp, True), '')))

    authdata = open(options.auth_file).read() if options.auth_file else None
    postdata = open(options.post_file).read() if options.post_file else None
    dest = open(options.output_file, 'w')
    lock = threading.Lock()

    try:
        route(pseudourl, authdata, postdata, dest, lock, options.timeout, options.retries, options.retry_wait,
            options.threads, options.verbose)

    except Error as e:
        msg(True, str(e))

    return 0

if __name__ == "__main__":
    sys.exit(main())

