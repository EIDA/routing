#!/usr/bin/env python

import subprocess
from twisted.internet import reactor
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.resource import Resource

HTTP_PORT = 8080
EIDA_FETCH = ('./eida_fetch.py', '-v', '-p', '/dev/stdin', '-o', '/dev/stdout')

class DataPipe(object):
    def __init__(self, req, proc):
        self.req = req
        self.proc = proc

    def resumeProducing(self):
        buf = self.proc.stdout.read(4096)

        if not buf:
            self.req.unregisterProducer()
            self.req.finish()
            self.proc.terminate()
            self.proc.stdout.close()
            print "eida_fetch finished"
            return

        self.req.write(buf)

    def stopProducing(self):
        self.proc.terminate()
        self.proc.stdout.close()
        print "eida_fetch aborted"

class Query(Resource):
    def render_POST(self, req):
        proc = subprocess.Popen(EIDA_FETCH, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.stdin.write(req.content.getvalue())
        proc.stdin.close()
        req.setHeader('Content-Type', 'application/vnd.fdsn.mseed')
        req.registerProducer(DataPipe(req, proc), False)
        return NOT_DONE_YET

root = Resource()
root.putChild('query', Query())
factory = Site(root)
reactor.listenTCP(HTTP_PORT, factory, interface='localhost')

print "fdsnws://localhost:%s/query ready" % HTTP_PORT

reactor.run()

