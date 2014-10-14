import io
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
        u = urlparse.urlparse(obspy.fdsn.client.Client._create_url_from_parameters(self, service, *args))
        return urlparse.urlunparse((u.scheme, u.netloc, '/eidaws/routing/1/query', '', u.query + '&service=' + service, ''))

    def _download(self, url, return_string=False, data=None):
        dest = io.BytesIO()
        eida_fetch.route(eida_fetch.URL(url), self.__authdata, data, dest, self.timeout,
            self.__retry_count, self.__retry_wait, self.__maxthreads)

        if return_string:
            return dest.getvalue()

        else:
            return dest

