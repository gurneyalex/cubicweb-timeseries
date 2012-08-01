import zlib
import pickle
from logilab.common.decorators import cachedproperty

class AbstractTSMixin(object):

    @cachedproperty
    #@cached(cacheattr='_array') XXX once lgc 0.56 is out
    def array(self):
        raw_data = self.data.getvalue()
        try:
            raw_data = zlib.decompress(raw_data)
        except zlib.error:
            # assume uncompressed data
            pass
        return pickle.loads(raw_data)

    def cw_clear_all_caches(self):
        if 'array' in vars(self):
            del self.array
        super(AbstractTSMixin, self).cw_clear_all_caches()


