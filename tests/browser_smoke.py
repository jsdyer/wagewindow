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
    assert page.locator('#region-a option').count()>=86
    assert page.locator('#occupation option').count()>=516
    assert 'Halifax' in page.locator('#comparison').inner_text()
    page.locator('#search').fill('00010')
    page.wait_for_function("document.querySelector('#wages').textContent.includes('84,000')")
    page.locator('#region-a').select_option('ER00')
    page.locator('#offer-unit').select_option('year');page.locator('#offer').fill('84000')
    assert 'CAD per year' in page.locator('#comparison').inner_text()
    assert '$84,000.00/year' in page.locator('#offer-summary').inner_text()
    page.locator('#plan-name').fill('<img src=x onerror=alert(1)>');page.locator('#save').click()
    assert page.locator('#saved article').count()==1;assert page.locator('img').count()==0
    page.reload();page.locator('#saved article').wait_for();assert 'Legislators' in page.locator('#saved').inner_text()
    with page.expect_download() as event:page.locator('#export').click()
    path=Path(temporary)/'plans.json';event.value.save_as(path)
    exported=json.loads(path.read_text());assert exported['plans'][0]['regions'][0]['estimate']['annual'] is True
    page.locator('#clear').click();assert page.locator('#saved article').count()==0
    page.locator('#import').set_input_files(str(path));page.locator('#saved article').wait_for()
    page.locator('#search').fill('31101')
    page.wait_for_function("document.querySelector('#occupation-title').textContent.includes('31101') && document.querySelectorAll('#wages tr').length>0")
    page.locator('#region-a').select_option('ER11')
    assert 'Source quality warning' in page.locator('#comparison').inner_text()
    assert 'comparison unavailable' in page.locator('#offer-summary').inner_text()
    page.locator('#region-filter').fill('Halifax');assert page.locator('#wages tr').count()==1
    page.locator('#hours').fill('0');assert page.locator('#save').is_disabled()
    page.locator('#hours').fill('37.5')
    page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
    assert not errors,errors
    browser.close()
   print('Browser checks passed: subpath, source data, calculations, safe saved plans, reload, JSON export/import and mobile layout')
  finally:server.shutdown()
if __name__=='__main__':main()
