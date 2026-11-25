import {convert,finite,money} from './model.mjs';
export function raiseComparison(oldPay,newPay,oldCpi,newCpi){
 const before=convert(oldPay.amount,oldPay.unit,'hour',oldPay.hours,oldPay.weeks),after=convert(newPay.amount,newPay.unit,'hour',newPay.hours,newPay.weeks);
 if(before<=0)throw new Error('Previous pay must be above zero.');
 oldCpi=finite(oldCpi,0.000001,100000);newCpi=finite(newCpi,0.000001,100000);
 const factor=newCpi/oldCpi,nominal=after/before,real=nominal/factor;
 return {before,after,inflation:(factor-1)*100,nominal:(nominal-1)*100,real:(real-1)*100,needed:before*factor,annualBefore:convert(oldPay.amount,oldPay.unit,'year',oldPay.hours,oldPay.weeks),annualAfter:convert(newPay.amount,newPay.unit,'year',newPay.hours,newPay.weeks)};
}
export function cpiPair(data,geo,from,to){
 if(!/^\d{4}-\d{2}$/.test(from)||!/^\d{4}-\d{2}$/.test(to)||from>to)throw new Error('Choose an end month on or after the start month.');
 const a=data.series[geo]?.[from],b=data.series[geo]?.[to];
 if(!a||!b||a.value===null||b.value===null)throw new Error('CPI is not published for both selected months. Choose available months; no values are estimated.');
 return [a,b];
}
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id),percent=n=>`${n>=0?'+':''}${n.toFixed(2)}%`;let data;
 const pay=prefix=>({amount:finite($(prefix+'-pay').value,0,100000000),unit:$(prefix+'-unit').value,hours:finite($(prefix+'-hours').value,1,100),weeks:finite($(prefix+'-weeks').value,1,52)});
 function render(){try{const [a,b]=cpiPair(data,$('cpi-geo').value,$('cpi-from').value,$('cpi-to').value),r=raiseComparison(pay('old'),pay('new'),a.value,b.value);$('raise-result').textContent=`Your hourly purchasing power ${Math.abs(r.real)<0.005?'stayed level':r.real>0?'increased':'decreased'} ${Math.abs(r.real).toFixed(2)}%. Normalized hourly pay: ${money(r.before)} → ${money(r.after)} (${percent(r.nominal)}), while all-items CPI changed ${percent(r.inflation)}. You need ${money(r.needed)}/hour at the end month to match the earlier purchasing power.`;$('raise-detail').textContent=`${$('cpi-geo').value}, ${$('cpi-from').value} to ${$('cpi-to').value}: CPI ${a.value} to ${b.value} (2002=100). Annual gross under each separate work schedule: ${money(r.annualBefore)} → ${money(r.annualAfter)}. Source checked ${data.checked_at.slice(0,10)}.${[a.flag,b.flag].some(Boolean)?' Published flags: '+[a.flag,b.flag].filter(Boolean).join(', '):''}`;}catch(e){$('raise-result').textContent=e.message;$('raise-detail').textContent='';}}
 function periods(){const dates=Object.entries(data.series[$('cpi-geo').value]).filter(([,r])=>r.value!==null).map(([d])=>d).sort();const old=$('cpi-from').value,end=$('cpi-to').value;for(const id of ['cpi-from','cpi-to'])$(id).replaceChildren(...dates.map(d=>new Option(d,d)));$('cpi-to').value=dates.includes(end)?end:dates.at(-1);$('cpi-from').value=dates.includes(old)?old:dates[Math.max(0,dates.length-13)];render();}
 async function start(){try{const response=await fetch('./data/cpi.json');if(!response.ok)throw new Error('CPI snapshot unavailable.');data=await response.json();$('cpi-geo').replaceChildren(...Object.keys(data.series).map(g=>new Option(g,g)));$('cpi-geo').value='British Columbia';$('cpi-geo').onchange=periods;for(const input of $('raise-form').querySelectorAll('input,select'))if(input.id!=='cpi-geo')input.addEventListener('input',render);periods();}catch(e){$('raise-result').textContent=e.message;}}
 start();
}
