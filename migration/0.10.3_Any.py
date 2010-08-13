constant_ts = rql('Any X WHERE X is TimeSeries, '
                  'X granularity %(gran)s',
                  {'gran': u'constant'}).entities()
for ts in constant_ts:
    if ts.count > 1:
        ts.data = ts.array[0:1]
commit()
