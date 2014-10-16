import io
import threading
import urlparse
import eida_fetch
import obspy.fdsn.client

class Client(obspy.fdsn.client.Client):
    def __init__(self, base_url="GFZ", retry_count=10, retry_wait=60, maxthreads=10, auth_file=None, **kwargs):
        obspy.fdsn.client.Client.__init__(self, base_url, **kwargs)
        self.__retry_count = retry_count
        self.__retry_wait = retry_wait
        self.__maxthreads = maxthreads
        self.__authdata = open(auth_file).read() if auth_file else None

    def _create_url_from_parameters(self, service, *args):
        if service in ('dataselect', 'station'):
            # construct a pseudo-URL for the routing service
            u = urlparse.urlparse(obspy.fdsn.client.Client._create_url_from_parameters(self, service, *args))
            return urlparse.urlunparse((u.scheme, u.netloc, '/eidaws/routing/1/query', '', u.query + '&service=' + service, ''))

        else: # 'event' is not routed
            return obspy.fdsn.client.Client._create_url_from_parameters(self, service, *args)

    def _download(self, url, return_string=False, data=None):
        if '&service=' in url:
            dest = io.BytesIO()
            lock = threading.Lock()

            try:
                eida_fetch.route(eida_fetch.URL(url), self.__authdata, data, dest, lock, self.timeout,
                    self.__retry_count, self.__retry_wait, self.__maxthreads, self.debug)

            except eida_fetch.Error as e:
                raise obspy.fdsn.client.FDSNException(str(e))

            if return_string:
                return dest.getvalue()

            else:
                return dest

        else:
            return obspy.fdsn.client.Client._download(self, url, return_string, data)

