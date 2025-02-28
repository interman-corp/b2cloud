import ssl
import urllib3
from urllib3.util import create_urllib3_context
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ctx = create_urllib3_context()
ctx.load_default_certs()
ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
ctx.maximum_version = ssl.TLSVersion.TLSv1_2


class HTTPSAdapter(HTTPAdapter):
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ctx
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(num_pools=connections, maxsize=maxsize, block=block, ssl_context=self.ssl_context)
