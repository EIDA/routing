#!/usr/bin/env python

import subprocess
from twisted.internet import reactor
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource

HTTP_PORT = 8080
EIDA_FETCH = ('./eida_fetch.py', '-p', '/dev/stdin', '-o', '/dev/stdout', '-v', '-t', '60', '-r', '0')

class DataPipe(object):
    def __init__(self, req, inp):
        self.req = req
        self.inp = inp

    def resumeProducing(self):
        buf = self.inp.read(4096)

        if not buf:
            self.req.unregisterProducer()
            self.req.finish()
            return

        self.req.write(buf)

    def stopProducing(self):
        pass

class Query(Resource):
    def render_POST(self, req):
        p = subprocess.Popen(EIDA_FETCH, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.stdin.write(req.content.getvalue())
        p.stdin.close()
        req.setHeader('Content-Type', 'application/vnd.fdsn.mseed')
        req.registerProducer(DataPipe(req, p.stdout), False)
        return NOT_DONE_YET

root = Resource()
root.putChild('query', Query())
factory = Site(root)
reactor.listenTCP(HTTP_PORT, factory, interface='localhost')

print "fdsnws://localhost:%s/query ready" % HTTP_PORT

reactor.run()

