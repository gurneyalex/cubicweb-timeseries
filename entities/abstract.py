import zlib
import pickle

class AbstractTSMixin(object):

    @property
    #@cached(cacheattr='_array') XXX once lgc 0.56 is out
    def array(self):
        if not hasattr(self, '_array'):
            raw_data = self.data.getvalue()
            try:
                raw_data = zlib.decompress(raw_data)
            except zlib.error:
                # assume uncompressed data
                pass
            self._array = pickle.loads(raw_data)
        return self._array
