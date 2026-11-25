#!/usr/bin/env python3
"""Fetch a complete ESDC wage edition and publish bounded, lazy-loaded data shards."""
import argparse,csv,hashlib,io,json,math,re,shutil,tempfile,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['low','median','high','annual','source','reference_period','revision_date','comment','benefits_percent']

def number(value):
    if value.strip() in {'','NA','N/A','..','x','F'}:return None
    result=float(value)
    if not math.isfinite(result) or result<0:raise ValueError('Invalid wage or benefit amount')
    return result

def choose_resource(metadata):
    if not metadata.get('success'):raise ValueError('Metadata request failed')
    choices=[]
    for r in metadata['result']['resources']:
        name=r.get('name','') or r.get('name_translated',{}).get('en','')
        match=re.search(r'(20\d{2})',name)
        url=r.get('url','');host=urlparse(url)
        if match and r.get('format','').upper()=='CSV' and host.scheme=='https' and host.hostname=='open.canada.ca':
            choices.append((int(match[1]),url))
    if not choices:raise ValueError('No supported wage CSV in metadata')
    return max(choices)

def normalize(raw,config,edition,url,checked_at):
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    needed={'NOC_CNP','NOC_Title_eng','NOC_Title_fra','prov','ER_Code_Code_RE','ER_Name','Nom_RE','Low_Wage_Salaire_Minium','Median_Wage_Salaire_Median','High_Wage_Salaire_Maximal','Annual_Wage_Flag_Salaire_annuel','Data_Source_E','Reference_Period','Revision_Date_Date_revision','Wage_Comment_E'}
    if not needed.issubset(reader.fieldnames or []):raise ValueError('Required source columns changed')
    sources=[];comments=[];occupations={};regions={};shards={};count=0;published=0;annual=0;anomalies=[]
    def intern(items,value):
        if value not in items:items.append(value)
        return items.index(value)
    for r in reader:
        count+=1
        if count>config['maximum_rows']:raise ValueError('Source exceeds row limit')
        noc=r['NOC_CNP'].removeprefix('NOC_');region=r['ER_Code_Code_RE']
        if not re.fullmatch(r'\d{5}',noc) or not re.fullmatch(r'ER\d{2,6}',region):raise ValueError('Unknown NOC/region key format')
        occupations[noc]={'name':r['NOC_Title_eng'],'name_fr':r['NOC_Title_fra']}
        region_value={'name':r['ER_Name'],'name_fr':r['Nom_RE'],'province':r['prov']}
        if region in regions and regions[region]!=region_value:raise ValueError('Conflicting region definitions')
        regions[region]=region_value
        wages=[number(r[k]) for k in ['Low_Wage_Salaire_Minium','Median_Wage_Salaire_Median','High_Wage_Salaire_Maximal']]
        known=[v for v in wages if v is not None]
        if known!=sorted(known):anomalies.append({'noc':noc,'region':region,'issue':'Published low/median/high are not in ascending order; preserved as reported.'})
        flag=r['Annual_Wage_Flag_Salaire_annuel']
        if flag not in {'0','1'}:raise ValueError('Unknown annual wage flag')
        source=intern(sources,r['Data_Source_E']);comment=intern(comments,r['Wage_Comment_E'])
        benefit=number(r.get('EmployeesWithNonWageBen_Pct',r.get('EmployeesWithNonWageBenefit_Pct','')))
        if benefit is not None and benefit>100:raise ValueError('Invalid benefits percentage')
        row=wages+[int(flag),source,r['Reference_Period'],r['Revision_Date_Date_revision'],comment,benefit]
        by_noc=shards.setdefault(noc[0],{}).setdefault(noc,{})
        if region in by_noc:raise ValueError('Duplicate occupation-region estimate')
        by_noc[region]=row
        published+=wages[1] is not None;annual+=flag=='1'
    if count<config['minimum_rows']:raise ValueError('Incomplete source download')
    digest=hashlib.sha256(raw).hexdigest()
    index={'schema':1,'edition':edition,'checked_at':checked_at,'last_attempt_at':checked_at,'status':'ok','source_url':url,'dataset_url':config['dataset_url'],'sha256':digest,'data_version':digest[:16],'row_count':count,'published_median_count':published,'annual_row_count':annual,'quality_warnings':anomalies,'occupation_count':len(occupations),'region_count':len(regions),'fields':FIELDS,'occupations':occupations,'regions':regions,'sources':sources,'comments':comments,'shards':sorted(shards)}
    return index,shards

def download(url,limit,timeout):
    req=urllib.request.Request(url,headers={'User-Agent':'CoolCode WageWindow/1.0 (+https://coolcode.ca/wagewindow/)'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status!=200:raise ValueError('Unexpected HTTP response')
        if urlparse(r.url).scheme!='https' or urlparse(r.url).hostname not in {'open.canada.ca','opencanada.blob.core.windows.net'}:raise ValueError('Source redirected outside publisher and its official download storage')
        body=r.read(limit+1)
        if len(body)>limit:raise ValueError('Source exceeds byte limit')
        return body

def refresh(root=ROOT,fetch=download,now=None,fixture=None):
    now=now or datetime.now(timezone.utc).isoformat(timespec='seconds')
    config=json.loads((root/'config/sources.json').read_text());directory=root/'web/data';path=directory/'index.json'
    previous=json.loads(path.read_text()) if path.exists() else None
    try:
        meta=fetch(config['metadata_url'],config['max_metadata_bytes'],config['timeout_seconds'])
        edition,url=choose_resource(json.loads(meta))
        raw=fixture.read_bytes() if fixture else fetch(url,config['max_csv_bytes'],config['timeout_seconds'])
        index,shards=normalize(raw,config,edition,url,now)
        if previous and edition<previous['edition']:raise ValueError('Edition moved backwards')
        # Stage every shard before changing the current snapshot. A failed parse never replaces data.
        with tempfile.TemporaryDirectory(dir=root/'web') as tmp:
            stage=Path(tmp)
            for name,data in shards.items():(stage/(name+'.json')).write_text(json.dumps({'schema':1,'data_version':index['data_version'],'occupations':data},ensure_ascii=False,separators=(',',':'))+'\n')
            (stage/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
            directory.mkdir(exist_ok=True)
            for file in stage.iterdir():file.replace(directory/file.name)
            for file in directory.glob('[0-9].json'):
                if file.stem not in shards:file.unlink()
        print(f"{index['row_count']} rows, {index['occupation_count']} occupations, {index['region_count']} regions; {edition} edition")
        return True
    except Exception as error:
        if not previous:raise
        previous.update(status='retained',last_attempt_at=now,last_error=type(error).__name__)
        path.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
        print('Source refresh failed; retained the original checked_at and validated wage data: '+type(error).__name__)
        return False

def main():
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--metadata-fixture',type=Path);a=p.parse_args()
    fetch=(lambda url,limit,timeout:a.metadata_fixture.read_bytes()) if a.metadata_fixture else download
    refresh(fetch=fetch,fixture=a.fixture)
if __name__=='__main__':main()
