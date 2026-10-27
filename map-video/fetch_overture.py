import sys, time, pyarrow.dataset as ds, pyarrow.fs as pfs, pyarrow.parquet as pq
theme, typ, cols = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
import os
x0,y0,x1,y1 = map(float, os.environ.get("BB","69.10,41.21,69.34,41.36").split(","))
s3 = pfs.S3FileSystem(anonymous=True, region='us-west-2')
d = ds.dataset(f'overturemaps-us-west-2/release/2026-10-21.0/theme={theme}/type={typ}/', filesystem=s3, format='parquet')
if len(sys.argv) > 4:  # intersects
    f = (ds.field('bbox','xmax') > x0) & (ds.field('bbox','xmin') < x1) & (ds.field('bbox','ymax') > y0) & (ds.field('bbox','ymin') < y1)
else:
    f = (ds.field('bbox','xmin') > x0) & (ds.field('bbox','xmax') < x1) & (ds.field('bbox','ymin') > y0) & (ds.field('bbox','ymax') < y1)
t=time.time()
tab = d.to_table(columns=cols+['bbox'], filter=f)
pq.write_table(tab, f'{typ}.parquet')
print(typ, tab.num_rows, round(time.time()-t), 's')
