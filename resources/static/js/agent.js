// Markdown → HTML with language classes so highlight.js can color
marked.setOptions({ gfm:true, breaks:false, headerIds:false, mangle:false, langPrefix:'language-' });

/* ===================== Prompt UI ===================== */
const promptUI  = document.getElementById('prompt-ui');
const btnHide   = document.getElementById('togglePromptBtn');
const btnShow   = document.getElementById('showPromptBtn');
const selPreset = document.getElementById('promptPreset');
const txtPrompt = document.getElementById('promptText');
const btnSend   = document.getElementById('sendPromptBtn');
const btnDel    = document.getElementById('deletePromptBtn');
const statusEl  = document.getElementById('sendStatus');
const PRESET_LIMIT = 20;

let presets = Array.isArray(window.__INITIAL_PROMPTS__) ? window.__INITIAL_PROMPTS__ : [];

function renderPresets(list){
  presets = Array.from(new Set(list)).slice(0, PRESET_LIMIT);
  selPreset.innerHTML = `<option value="">— Choose a preset —</option>`;
  presets.forEach(p=>{
    const o=document.createElement('option');
    o.value=o.textContent=p.length>120?p.slice(0,117)+'…':p;
    selPreset.append(o);
  });
  btnDel.disabled=!selPreset.value;
}
selPreset.onchange=()=>{ txtPrompt.value=selPreset.value; btnDel.disabled=!selPreset.value; };
txtPrompt.onkeydown=e=>{ if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){ e.preventDefault(); sendPrompt(); } };
btnHide.onclick=()=>{ promptUI.classList.add('collapsed'); btnShow.classList.remove('hidden'); };
btnShow.onclick=()=>{ promptUI.classList.remove('collapsed'); btnShow.classList.add('hidden'); };

async function api(method, body){
  const rsp = await fetch('/summary_board/api/prompt',{ method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
  if(!rsp.ok) throw new Error(`HTTP ${rsp.status}`); return rsp.json();
}
function busy(on,msg=''){ btnSend.disabled=btnDel.disabled=on; statusEl.textContent=msg;
  if(!on&&msg) setTimeout(()=>statusEl.textContent='',1500); }
async function sendPrompt(){
  const p=txtPrompt.value.trim(); if(!p) return;
  try{ busy(true,'Sending…'); const d=await api('POST',{prompt:p}); renderPresets(d.prompts); selPreset.value=p; busy(false,'Sent ✓'); }
  catch(e){ console.error(e); busy(false,'Failed'); }
}
async function deletePrompt(){
  const p=selPreset.value; if(!p) return;
  try{ busy(true,'Deleting…'); const d=await api('DELETE',{prompt:p}); renderPresets(d.prompts); txtPrompt.value=''; selPreset.value=''; busy(false,'Deleted ✓'); }
  catch(e){ console.error(e); busy(false,'Failed'); }
}
btnSend.addEventListener('click',sendPrompt);
btnDel .addEventListener('click',deletePrompt);
if(presets.length) renderPresets(presets);
else fetch('/summary_board/api/prompts').then(r=>r.ok?r.json():{prompts:[]}).then(d=>renderPresets(d.prompts||[])).catch(()=>renderPresets([]));

/* ===================== Results via WebSocket ===================== */
const root = document.getElementById('root');
const emptyState = document.getElementById('empty-state');
const startBtn = document.getElementById('startBtn');
const ws   = new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/summary_board/ws');
const order=['info','suggestion','warning','error'];

/* Persist state across re-renders */
const expanded = new Set();        // item keys that are open
const collapsed = new Set();       // group names that are collapsed

ws.onmessage = e => { 
  try { 
    const data = JSON.parse(e.data) || [];
    console.log('WebSocket received data:', data);
    renderResults(data); 
  } catch(error) { 
    console.error('WebSocket parse error:', error);
  } 
};

// Initialize empty state on page load
renderResults([]);

/* Render list of rows (full replace each time) */
function renderResults(rows){
  root.innerHTML='';

  // Show/hide empty state based on content
  if(!rows || rows.length === 0) {
    root.classList.add('hidden');
    emptyState.classList.remove('hidden');
    return;
  } else {
    root.classList.remove('hidden');
    emptyState.classList.add('hidden');
  }

  const groups=[...new Set(rows.map(r=>r.group))].sort((a,b)=>order.indexOf(a)-order.indexOf(b));
  groups.forEach(g=>{
    const card=div('group');
    const hdr =div('group-header');
    hdr.append(svg(), text(`Group: ${g}`));
    card.append(hdr);

    const list=div('items');
    if(collapsed.has(g)) list.classList.add('collapsed');
    hdr.onclick=()=>{ collapsed.has(g)?collapsed.delete(g):collapsed.add(g);
                      list.classList.toggle('collapsed'); card.classList.toggle('collapsed'); };
    card.append(list);

    rows.filter(r=>r.group===g).forEach(rec=>{
      const key=(rec.title||'')+'||'+(rec.content||'');

      const item=div('item');
      if(expanded.has(key)) item.classList.add('open');   // restore open state

      /* header (single click target) */
      const head=div('item-head');

      const dot =div('color-dot'); dot.style.backgroundColor=rec.color_circle||'#9aa7b1';
      const main=div('item-main');
      const title=div('item-title'); title.textContent=rec.title||'';
      const summary=div('item-summary');
      const sv=rec.very_short_summary_of_content||'';
      summary.textContent = toPlainText(sv || extractPreview(rec.content||''));
      main.append(title,summary);

      const caret=div('item-caret'); caret.innerHTML='<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>';

      head.append(dot,main,caret);
      item.append(head);

      /* expanded body spans full width */
      const body=div('content-body'+(expanded.has(key)?'':' hidden'));
      const inner=div('content-body-inner');
      inner.innerHTML=DOMPurify.sanitize(marked.parse(rec.content||''));
      body.append(inner);
      item.append(body);

      /* open/close with ONE click on the head (not on links/buttons) */
      head.addEventListener('click', (ev)=>{
        if (ev.target.closest('a, button, input, textarea, select, pre code')) return;
        const isOpen=item.classList.toggle('open');
        body.classList.toggle('hidden', !isOpen);
        if(isOpen){ expanded.add(key); highlight(body); } else { expanded.delete(key); }
      });

      list.append(item);
    });

    root.append(card);
  });
}

function highlight(el){
  el.querySelectorAll('pre code:not([data-hl])').forEach(c=>{ hljs.highlightElement(c); c.dataset.hl=1; });
}

/* ---------- helpers ---------- */
function div(c){ const e=document.createElement('div'); e.className=c; return e; }
function text(t){ const s=document.createElement('span'); s.textContent=t; return s; }
function svg(){ const d=document.createElement('div'); d.innerHTML='<svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>'; return d.firstChild; }

/* Convert HTML/Markdown to plain text preserving soft breaks */
function toPlainText(s=''){
  const looksHTML=/<[a-z][\s\S]*>/i.test(s);
  const html=looksHTML?s:marked.parse(s);
  const tmp=document.createElement('div'); tmp.innerHTML=DOMPurify.sanitize(html);
  let txt=tmp.textContent||'';
  return txt.replace(/\u00A0/g,' ').replace(/[ \t]+\n/g,'\n').trim();
}

/* First 2 paragraphs from Markdown for preview */
function extractPreview(md=''){
  return md.split(/\n\s*\n/).slice(0,2).join('\n\n');
}

/* Start button click handler */
startBtn.addEventListener('click', async function() {
  try {
    const response = await fetch('/summary_board/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) {
      console.error('Start request failed:', response.status);
    }
  } catch (error) {
    console.error('Error starting:', error);
  }
});

/* keep WS alive */
setInterval(()=>{ if(ws.readyState===1) ws.send('ping'); }, 10000);
