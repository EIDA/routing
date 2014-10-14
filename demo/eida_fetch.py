#!/usr/bin/env python

import sys
import time
import optparse
import urlparse
import urllib
import urllib2
import cookielib
import threading
import Queue

VERSION = "0.1 (2014.287)"

class URL(object):
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
            q = urlparse.parse_qs(u[4])
            q.update(kw)
            u[4] = urllib.urlencode(q, True)

        return urlparse.urlunparse(u)

def retry(urlopen, url, data, timeout, count, wait):
    n = 0

    while True:
        if n >= count:
            return urlopen(url, data, timeout)

        try:
            n += 1

            fd = urlopen(url, data, timeout)

            if fd.getcode() == 200 or fd.getcode() == 204:
                return fd

            print "retrying %s (%d) after %d seconds due to HTTP status code %d" % (url, n, wait, fd.getcode())
            time.sleep(wait)

        except urllib2.URLError as e:
            print "retrying %s (%d) after %d seconds due to %s" % (url, n, wait, str(e))
            time.sleep(wait)

def fetch(url, authdata, postdata, dest, timeout, retry_count, retry_wait, finished):
    try:
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        if authdata:
            auth_url = url.auth()
            query_url = url.query(True)

            print "authenticating at %s" % auth_url

            try:
                fd = retry(opener.open, auth_url, authdata, timeout, retry_count, retry_wait)

                try:
                    if fd.getcode() == 200:
                        print "authentication at %s successful" % auth_url

                    else:
                        print "authentication at %s failed with HTTP status code %d" % (auth_url, fd.getcode())

                finally:
                    fd.close()

            except urllib2.URLError as e:
                print "authentication at %s failed: %s" % (auth_url, str(e))

        else:
            query_url = url.query(False)

        print "getting data from %s" % query_url

        try:
            fd = retry(opener.open, query_url, postdata, timeout, retry_count, retry_wait)

            try:
                if fd.getcode() == 204:
                    print "received no data from %s" % query_url

                elif fd.getcode() != 200:
                    print "getting data from %s failed with HTTP status code %d" % fd.getcode()

                else:
                    size = 0

                    content_type = fd.info().getheader('Content-Type')

                    if content_type == "application/vnd.fdsn.mseed":
                        while True:
                            buf = fd.read(4096)
                            if not buf: break
                            dest.write(buf)
                            size += len(buf)

                        print "got %d bytes from %s" % (size, query_url)

                    # XML content (eg., station webservice) is not supported yet
                    else:
                        print "getting data from %s failed: unsupported content type '%s'" % (query_url, content_type)

            finally:
                fd.close()

        except urllib2.URLError as e:
            print "getting data from %s failed: %s" % (query_url, str(e))

    finally:
        finished.put(threading.current_thread())

def route(url, authdata, postdata, dest, timeout, retry_count, retry_wait, maxthreads):
    threads = []
    running = 0
    finished = Queue.Queue()
    query_url = url.query(format='post')

    print "getting routes from %s" % query_url

    try:
        fd = retry(urllib2.urlopen, query_url, postdata, timeout, retry_count, retry_wait)

        try:
            if fd.getcode() == 204:
                print "received no routes from %s" % query_url

            elif fd.getcode() != 200:
                print "getting routes from %s failed with code %d" % (query_url, fd.getcode())

            else:
                dsurl = None
                postlines = []

                while True:
                    line = fd.readline()

                    if not dsurl:
                        dsurl = URL(line.strip())

                    elif not line.strip():
                        if dsurl and postlines:
                            threads.append(threading.Thread(target=fetch, args=(dsurl, authdata,
                                "".join(postlines), dest, timeout, retry_count, retry_wait, finished)))

                            dsurl = None
                            postlines = []

                        if not line:
                            break

                    else:
                        postlines.append(line)

        finally:
            fd.close()

    except urllib2.URLError as e:
        print "getting routes from %s failed: %s" % (query_url, str(e))

    for t in threads:
        if running >= maxthreads:
            finished.get(True)
            running -= 1

        t.start()
        running += 1

    while running:
        finished.get(True)
        running -= 1

def main():
    parser = optparse.OptionParser(usage="Usage: %prog [-h|--help] [OPTIONS] url", version="%prog v" + VERSION)

    parser.add_option("-t", "--timeout", type="int", dest="timeout", default=600,
      help="request timeout in seconds (default %default)")

    parser.add_option("-r", "--retries", type="int", dest="retry_count", default=10,
      help="number of retries (default %default)")

    parser.add_option("-w", "--retry-wait", type="int", dest="retry_wait", default=60,
      help="seconds to wait before each retry (default %default)")

    parser.add_option("-n", "--threads", type="int", dest="threads", default=10,
      help="maximum number of download threads (default %default)")

    parser.add_option("-a", "--auth-file", type="string", dest="auth_file", default=None,
      help="auth file (secure mode)")

    parser.add_option("-p", "--post-file", type="string", dest="post_file",
      help="data file for POST request")

    parser.add_option("-o", "--output-file", type="string", dest="output_file",
      help="file where downloaded data is written")

    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.print_usage()
        return 1

    url = URL(args[0])
    authdata = open(options.auth_file).read() if options.auth_file else None
    postdata = open(options.post_file).read() if options.post_file else None
    dest = open(options.output_file, 'w')
    route(url, authdata, postdata, dest, options.timeout, options.retry_count, options.retry_wait, options.threads)

    return 0

if __name__ == "__main__":
    sys.exit(main())

