'use strict';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let report=null, busy=false, chatReady=false;
async function request(path,body,csv=false){
 const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':csv?'text/csv':'application/json'},body:csv?body:JSON.stringify(body)});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Something went wrong. Please try again.');return data;
}
function showError(message){$('error').textContent=message;$('error').hidden=false;}
function cardHTML(card,index){
 const table=card.table.length?`<div class="table-scroll"><table><thead><tr>${card.columns.map(v=>`<th>${esc(v)}</th>`).join('')}</tr></thead><tbody>${card.table.map(row=>`<tr>${Object.values(row).map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'';
 const details=table||card.details.length?`<details class="card-details"><summary>See supporting numbers</summary>${table}<ul>${card.details.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></details>`:'';
 return `<article class="recommendation"><div class="card-heading"><h2><span class="card-number">${String(index+1).padStart(2,'0')}</span>${esc(card.title)}</h2><span class="status ${card.status.startsWith('Need')?'missing':''}">${esc(card.status)}</span></div><p class="action">${esc(card.action)}</p><p class="reason">${esc(card.reason)}</p>${(card.highlights||[]).length?`<ul class="highlights">${card.highlights.map(v=>`<li>${esc(v)}</li>`).join('')}</ul>`:''}<p class="next-step"><strong>NEXT STEP</strong>${esc(card.next_step)}</p>${details}</article>`;
}
function display(data){
 report=data;$('report-context').textContent=`${data.summary.orders.toLocaleString()} orders · ${data.summary.branches} branches · ${data.period}`;
 $('cards').innerHTML=data.cards.map(cardHTML).join('');$('notes').innerHTML=data.notes.map(v=>`<li>${esc(v)}</li>`).join('');
 $('report').hidden=false;$('upload-section').hidden=true;$('download').hidden=false;$('conversation').replaceChildren();$('question').value='';$('followup').open=false;
 $('gemini-status').textContent=chatReady?'Ready to explain your recommendations':'Follow-up unavailable: Gemini is not configured on this server.';$('ask').disabled=!chatReady;
}
async function analyze(file){
 if(busy)return;busy=true;$('error').hidden=true;$('progress').hidden=false;$('existing').disabled=true;$('file-input').disabled=true;
 try{
  if(file&&(!file.name.toLowerCase().endsWith('.csv')||file.size>40000000))throw new Error('Choose a CSV file smaller than 40 MB.');
  const data=await request(file?'/api/upload':'/api/analyze',file||{},!!file);display(data);
 }catch(error){showError(error.message);}finally{busy=false;$('progress').hidden=true;$('existing').disabled=false;$('file-input').disabled=false;$('file-input').value='';}
}
$('file-input').addEventListener('change',event=>{if(event.target.files[0])analyze(event.target.files[0]);});
$('existing').addEventListener('click',()=>analyze(null));
$('change-file').addEventListener('click',()=>{$('upload-section').hidden=false;$('report').hidden=true;$('download').hidden=true;$('error').hidden=true;});
for(const name of ['dragenter','dragover'])$('dropzone').addEventListener(name,event=>{event.preventDefault();$('dropzone').classList.add('drag');});
for(const name of ['dragleave','drop'])$('dropzone').addEventListener(name,event=>{event.preventDefault();$('dropzone').classList.remove('drag');if(name==='drop'&&event.dataTransfer.files[0])analyze(event.dataTransfer.files[0]);});
$('ask-form').addEventListener('submit',async event=>{
 event.preventDefault();const question=$('question').value.trim();if(!question||!report||busy||!chatReady)return;
 busy=true;$('ask').disabled=true;$('ask').textContent='Thinking…';
 const user=document.createElement('div');user.className='message user';user.textContent=question;$('conversation').append(user);$('question').value='';
 try{const answer=await request('/api/ask',{question});const el=document.createElement('div');el.className='message';el.textContent=answer.text;$('conversation').append(el);}
 catch(error){const el=document.createElement('div');el.className='message';el.textContent=error.message;$('conversation').append(el);}
 finally{busy=false;$('ask').disabled=false;$('ask').textContent='Ask →';}
});
$('download').addEventListener('click',()=>{
 if(!report)return;
 const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>Stories recommendations</title><style>body{max-width:850px;margin:40px auto;padding:0 24px;color:#243a2b;font:15px/1.7 system-ui}h1,h2{font-family:Georgia,serif}.recommendation{border-bottom:1px solid #ddd;padding:24px 0}.card-heading{display:flex;justify-content:space-between;gap:20px}.status{font-size:11px}.action{font-size:20px}.next-step strong{display:block}.card-details{font-size:12px}table{border-collapse:collapse;width:100%}th,td{padding:8px;text-align:left;border-bottom:1px solid #ddd}.card-number{margin-right:12px}</style><h1>Stories · Business recommendations</h1><p>${esc(report.period)} · ${report.summary.orders.toLocaleString()} orders</p>${report.cards.map(cardHTML).join('')}<h2>About these estimates</h2><ul>${report.notes.map(v=>`<li>${esc(v)}</li>`).join('')}</ul></html>`;
 const url=URL.createObjectURL(new Blob([html],{type:'text/html'}));const a=document.createElement('a');a.href=url;a.download='stories-recommendations.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
(async()=>{try{const meta=await request('/api/meta');chatReady=meta.chat_configured;$('existing').hidden=!meta.existing_available;$('column-names').textContent=meta.columns.join(' · ');}catch(error){showError('Could not reach the local server. Start it and reload this page.');}})();
