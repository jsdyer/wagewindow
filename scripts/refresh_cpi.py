"""Retain all-items monthly CPI with exact source geography and no interpolated values."""
import argparse,csv,io,json,math,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def normalize(raw,config,checked):
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  info=archive.getinfo('18100004.csv')
  if info.file_size>350_000_000:raise ValueError('Expanded source exceeds limit')
  with archive.open(info) as f:
   reader=csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'))
   series={};vectors={}
   for r in reader:
    geo=r['GEO'];month=r['REF_DATE']
    if geo not in config['geographies'] or month<config['start_month'] or r['Products and product groups']!='All-items' or r['UOM']!='2002=100':continue
    value=float(r['VALUE']) if r['VALUE'] else None
    if value is not None and (not math.isfinite(value) or value<=0):raise ValueError('Invalid CPI')
    values=series.setdefault(geo,{})
    if month in values:raise ValueError('Duplicate CPI observation')
    values[month]={'value':value,'flag':r['STATUS'] or r['SYMBOL']}
    vectors[geo]=r['VECTOR']
 if set(series)!=set(config['geographies']) or any(len(x)<24 for x in series.values()):raise ValueError('Incomplete CPI geography coverage')
 return {'schema':1,'checked_at':checked,'table':'18100004','unit':'2002=100','adjustment':'Not seasonally adjusted','source_url':config['source_url'],'series':series,'vectors':vectors}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path);a=p.parse_args()
 config=json.loads((ROOT/'config/cpi.json').read_text())
 if a.source:raw=a.source.read_bytes()
 else:
  req=urllib.request.Request(config['source_url'],headers={'User-Agent':'CoolCode WageWindow (+https://coolcode.ca/wagewindow/)'})
  with urllib.request.urlopen(req,timeout=120) as response:
   if response.status!=200 or not response.url.startswith('https://www150.statcan.gc.ca/'):raise ValueError('Unexpected source response')
   raw=response.read(40_000_001)
  if len(raw)>40_000_000:raise ValueError('Download exceeds limit')
 data=normalize(raw,config,datetime.now(timezone.utc).isoformat(timespec='seconds'))
 target=ROOT/'web/data/cpi.json';tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(data,separators=(',',':'))+'\n');tmp.replace(target)
 print(f"CPI: {len(data['series'])} geographies, checked {data['checked_at']}")
if __name__=='__main__':main()
