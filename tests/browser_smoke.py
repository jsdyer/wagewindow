"""Exercise the built application at its project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json,os,shutil,tempfile,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
def main():
 index=json.loads((ROOT/'web/data/index.json').read_text());all_rows={}
 for shard in index['shards']:all_rows.update(json.loads((ROOT/f'web/data/{shard}.json').read_text())['occupations'])
 annual_noc,annual_region,annual_row=next((noc,rid,row) for noc,regions in all_rows.items() for rid,row in regions.items() if row[3]==1 and row[1] is not None and rid=='ER00')
 annual_title=index['occupations'][annual_noc]['name'];annual_median=annual_row[1]
 screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temporary:
  shutil.copytree(ROOT/'dist',Path(temporary)/'wagewindow')
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temporary));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    options={}
    executable=os.environ.get('CHROMIUM_PATH')
    if executable:options['executable_path']=executable
    browser=p.chromium.launch(**options)
    page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/wagewindow/')
    page.locator('#wages tr').first.wait_for()
    assert page.locator('#region-a option').count()==index['region_count']
    assert page.locator('#occupation option').count()==index['occupation_count']
    assert 'Halifax' in page.locator('#comparison').inner_text()
    page.locator('#search').fill(annual_noc)
    page.wait_for_function("document.querySelectorAll('#wages tr').length>0")
    page.locator('#region-a').select_option(annual_region)
    page.locator('#offer-unit').select_option('year');page.locator('#offer').fill(str(annual_median))
    assert 'CAD per year' in page.locator('#comparison').inner_text()
    assert f'${annual_median:,.2f}/year' in page.locator('#offer-summary').inner_text()
    page.locator('#plan-name').fill('<img src=x onerror=alert(1)>');page.locator('#save').click()
    assert page.locator('#saved article').count()==1;assert page.locator('img').count()==0
    page.reload();page.locator('#saved article').wait_for();assert annual_title in page.locator('#saved').inner_text()
    with page.expect_download() as event:page.locator('#export').click()
    path=Path(temporary)/'plans.json';event.value.save_as(path)
    exported=json.loads(path.read_text());assert exported['plans'][0]['regions'][0]['estimate']['annual'] is True
    page.locator('#clear').click();assert page.locator('#saved article').count()==0
    page.locator('#import').set_input_files(str(path));page.locator('#saved article').wait_for()
    # A later official edition may correct today's anomaly; never block that refresh.
    if index.get('quality_warnings'):
     warning=index['quality_warnings'][0]
     page.locator('#search').fill(warning['noc'])
     page.wait_for_function("document.querySelectorAll('#wages tr').length>0")
     page.locator('#region-a').select_option(warning['region'])
     assert 'Source quality warning' in page.locator('#comparison').inner_text()
     assert 'comparison unavailable' in page.locator('#offer-summary').inner_text()
    page.locator('#region-filter').fill('Halifax');assert page.locator('#wages tr').count()==1
    page.locator('#hours').fill('0');assert page.locator('#save').is_disabled()
    page.locator('#hours').fill('37.5')
    page.locator('#cpi-geo').select_option('Nova Scotia')
    page.locator('#old-pay').fill('30');page.locator('#new-pay').fill('30')
    assert 'purchasing power' in page.locator('#raise-result').inner_text()
    page.locator('#old-hours').fill('0');assert 'Enter a number' in page.locator('#raise-result').inner_text()
    page.locator('#old-hours').fill('37.5')
    page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
    assert not errors,errors
    # Exercise the direct search landing page in a fresh browser context.
    case_page = browser.new_page(viewport={'width': 390, 'height': 844})
    case_page.route('https://**/*', lambda route: route.abort())
    case_page.goto(f'http://127.0.0.1:{server.server_port}/wagewindow/nurse-wages-halifax-lower-mainland.html')
    case_page.wait_for_function("() => {const q=s=>document.querySelector(s);return q('#occupation').value==='31301' && q('#region-a').value==='ER1250';}")
    assert case_page.locator('link[rel="canonical"]').get_attribute('href') == 'https://coolcode.ca/wagewindow/nurse-wages-halifax-lower-mainland.html'
    assert case_page.locator('h1').inner_text() in case_page.title()
    assert case_page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    browser.close()
   print('Browser checks passed: subpath, source data, calculations, safe saved plans, reload, JSON export/import and mobile layout')
  finally:server.shutdown()
if __name__=='__main__':main()
