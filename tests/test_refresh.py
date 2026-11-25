import copy,csv,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import ROOT,choose_resource,normalize,refresh,download
RAW=(Path(__file__).parent/'fixtures/wages.csv').read_bytes()
class RefreshTests(unittest.TestCase):
 def setUp(self):
  self.config=json.loads((ROOT/'config/sources.json').read_text());self.config['minimum_rows']=1
 def normalize(self,raw=RAW):return normalize(raw,self.config,2026,'https://open.canada.ca/wages.csv','2026-11-24T10:00:00+00:00')
 def test_newest_csv_is_selected_on_official_host_only(self):
  m={'success':True,'result':{'resources':[{'name':'2025 Wages','format':'CSV','url':'https://open.canada.ca/2025.csv'},{'name':'2027 Wages','format':'CSV','url':'https://evil.invalid/2027.csv'},{'name':'2026 Wages','format':'CSV','url':'https://open.canada.ca/2026.csv'}]}}
  self.assertEqual(choose_resource(m),(2026,'https://open.canada.ca/2026.csv'))
 def test_annual_hourly_missing_and_source_periods_survive(self):
  index,shards=self.normalize();leg=shards['0']['00010']['ER00'];self.assertEqual(leg[:4],[32867,84000,184000,1]);self.assertEqual(leg[5],'2021');self.assertTrue(any(r[1] is None for s in shards.values() for o in s.values() for r in o.values()));self.assertEqual(len(index['quality_warnings']),1)
 def test_truncated_and_unknown_unit_csv_rejected(self):
  with self.assertRaises(ValueError):self.normalize(b'<html>Error</html>')
  text=RAW.decode().replace(',1,Wages for this occupation',',2,Wages for this occupation')
  # Replace by column so fixture wording changes do not weaken this assertion.
  rows=list(csv.DictReader(io.StringIO(RAW.decode())));rows[0]['Annual_Wage_Flag_Salaire_annuel']='2';f=io.StringIO();w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
  with self.assertRaises(ValueError):self.normalize(f.getvalue().encode())
 def test_official_azure_redirect_allowed_but_unknown_host_rejected(self):
  from unittest.mock import patch
  class Response:
   status=200
   url='https://opencanada.blob.core.windows.net/opengovprod/resources/wages.csv'
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self,limit):return b'csv'
  with patch('urllib.request.urlopen',return_value=Response()):self.assertEqual(download('https://open.canada.ca/data.csv',100,10),b'csv')
  Response.url='https://unknown.invalid/wages.csv'
  with patch('urllib.request.urlopen',return_value=Response()):
   with self.assertRaises(ValueError):download('https://open.canada.ca/data.csv',100,10)
 def test_duplicate_rows_rejected(self):
  lines=RAW.decode().splitlines();raw=('\n'.join(lines+[lines[1]])+'\n').encode()
  with self.assertRaises(ValueError):self.normalize(raw)
 def test_failed_fetch_retains_original_check_date_and_shards(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'config').mkdir();(root/'config/sources.json').write_text(json.dumps(self.config));shutil.copytree(ROOT/'web/data',root/'web/data');before=(root/'web/data/2.json').read_bytes();old=json.loads((root/'web/data/index.json').read_text())
   def fail(*args):raise TimeoutError('fixture')
   self.assertFalse(refresh(root,fetch=fail,now='2026-11-25T10:00:00+00:00'))
   new=json.loads((root/'web/data/index.json').read_text());self.assertEqual(new['checked_at'],old['checked_at']);self.assertEqual(new['status'],'retained');self.assertEqual(before,(root/'web/data/2.json').read_bytes())
 def test_full_snapshot_counts_and_coverage_derive_from_rows(self):
  index=json.loads((ROOT/'web/data/index.json').read_text());shards=[json.loads((ROOT/f'web/data/{name}.json').read_text())['occupations'] for name in index['shards']];rows=[r for s in shards for o in s.values() for r in o.values()]
  self.assertEqual(len(rows),index['row_count']);self.assertEqual(sum(r[1] is not None for r in rows),index['published_median_count']);self.assertEqual(sum(r[3] for r in rows),index['annual_row_count']);self.assertEqual(len(index['occupations']),index['occupation_count']);self.assertEqual(len(index['regions']),index['region_count']);self.assertIn('ER1250',index['regions']);self.assertIn('ER5920',index['regions']);self.assertGreater(index['occupation_count'],500);self.assertGreater(index['region_count'],80)
if __name__=='__main__':unittest.main()
