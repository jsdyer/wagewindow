import csv,io,json,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh_cpi import normalize
class CpiTests(unittest.TestCase):
 def raw(self,rows):
  b=io.BytesIO();s=io.StringIO();fields=['REF_DATE','GEO','Products and product groups','UOM','VALUE','STATUS','SYMBOL','VECTOR'];w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows)
  with zipfile.ZipFile(b,'w') as z:z.writestr('18100004.csv',s.getvalue())
  return b.getvalue()
 def rows(self):
  return [dict(REF_DATE=f'{2024+i//12}-{1+i%12:02}',GEO='Additional place',**{'Products and product groups':'All-items','UOM':'2002=100','VALUE':'100','STATUS':'','SYMBOL':'','VECTOR':'v123'}) for i in range(24)]
 def test_config_drives_new_geo_and_missing_is_not_zero(self):
  r=self.rows();r[0]['VALUE']='';r[0]['SYMBOL']='..';d=normalize(self.raw(r),{'geographies':['Additional place'],'start_month':'2024-01','source_url':'https://example.test'},'2026-01-01');self.assertIsNone(d['series']['Additional place']['2024-01']['value']);self.assertEqual(d['checked_at'],'2026-01-01')
 def test_incomplete_duplicate_invalid_fail(self):
  c={'geographies':['Additional place'],'start_month':'2024-01','source_url':'https://example.test'}
  for r in [self.rows()[:2],self.rows()+self.rows()[:1]]:
   with self.assertRaises(ValueError):normalize(self.raw(r),c,'2026-01-01')
  r=self.rows();r[0]['VALUE']='nan'
  with self.assertRaises(ValueError):normalize(self.raw(r),c,'2026-01-01')
if __name__=='__main__':unittest.main()
