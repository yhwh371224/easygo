function initTimePickers(container){
  (container||document).querySelectorAll('.tp-wrap').forEach(wrap=>{
    if(wrap._tpInit)return;
    wrap._tpInit=true;
    const hidden=document.getElementById('id_'+wrap.dataset.field);
    function update(){
      const hEl=wrap.querySelector('.tp-hour');
      const mEl=wrap.querySelector('.tp-min');
      let h=parseInt(hEl.value)||parseInt(hEl.placeholder)||12;
      let m=parseInt(mEl.value)||parseInt(mEl.placeholder)||0;
      h=Math.min(12,Math.max(1,h));
      m=Math.min(59,Math.max(0,m));
      let ampm=wrap.querySelector('.tp-ampm.tp-active').dataset.val;
      if(h===12&&ampm==='AM'){
        ampm='PM';
        wrap.querySelectorAll('.tp-ampm').forEach(b=>b.classList.toggle('tp-active',b.dataset.val==='PM'));
        const note=wrap.parentElement.querySelector('.tp-midnight-note');
        if(note){
          note.style.display='block';
          clearTimeout(wrap._tpNoteTimer);
          wrap._tpNoteTimer=setTimeout(()=>{note.style.display='none';},4000);
        }
      }
      if(ampm==='AM'&&h===12)h=0;
      else if(ampm==='PM'&&h!==12)h+=12;
      hidden.value=`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
      checkFlightPickupGap();
    }
    wrap._tpUpdate=update;
    wrap.querySelectorAll('.tp-ampm').forEach(btn=>{
      btn.addEventListener('click',()=>{
        wrap.querySelectorAll('.tp-ampm').forEach(b=>b.classList.remove('tp-active'));
        btn.classList.add('tp-active');
        update();
      });
    });
    wrap.querySelectorAll('.tp-hour,.tp-min').forEach(inp=>{
      inp.addEventListener('input',update);
      inp.addEventListener('blur',function(){
        const isHour=this.classList.contains('tp-hour');
        let v=parseInt(this.value);
        this.value=isHour?String(Math.min(12,Math.max(1,v||12))):String(Math.min(59,Math.max(0,v||0))).padStart(2,'0');
        update();
      });
    });
    wrap.querySelector('.tp-hour').addEventListener('input',function(){
      const v=parseInt(this.value);
      if(this.value.length===2||v>1){wrap.querySelector('.tp-min').focus();}
    });
  });
}

// Flight vs pickup time more than 6h apart almost always means AM/PM was
// picked wrong on one of them — warn under the pickup time, and ask again on submit.
const TP_GAP_PAIRS=[['flight_time','pickup_time'],['return_flight_time','return_pickup_time']];
const TP_GAP_MAX_MIN=6*60;
function tpMinutes(v){
  const m=/^(\d{2}):(\d{2})$/.exec(v||'');
  return m?parseInt(m[1])*60+parseInt(m[2]):null;
}
function tpFormat(min){
  const h=Math.floor(min/60),m=min%60;
  return `${h%12||12}:${String(m).padStart(2,'0')} ${h<12?'AM':'PM'}`;
}
function checkFlightPickupGap(){
  const gaps=[];
  TP_GAP_PAIRS.forEach(([flightName,pickupName])=>{
    const pickup=document.getElementById('id_'+pickupName);
    if(!pickup)return;
    let note=pickup.parentElement.querySelector('.tp-ampm-gap-note');
    const flight=document.getElementById('id_'+flightName);
    const flightWrap=flight&&flight.parentElement.querySelector('.tp-wrap');
    const f=flight&&flightWrap&&flightWrap.offsetParent!==null?tpMinutes(flight.value):null;
    const p=tpMinutes(pickup.value);
    let show=false;
    if(f!==null&&p!==null){
      const d=Math.abs(f-p);
      show=Math.min(d,1440-d)>TP_GAP_MAX_MIN;  // circular, so 11:30 PM vs 1:00 AM is 1.5h
    }
    if(show)gaps.push({pickupName,flight:f,pickup:p});
    if(!note){
      if(!show)return;
      note=document.createElement('small');
      note.className='tp-ampm-gap-note';
      note.style.cssText='padding-left:18px;color:#dc3545;font-weight:600;display:none';
      note.textContent='⚠ AM / PM may be selected incorrectly. Please check again.';
      pickup.parentElement.insertBefore(note,pickup);
    }
    note.style.display=show?'block':'none';
  });
  return gaps;
}

// Shown on submit while a gap remains. "Correct my times" cancels and jumps to
// the pickup time; "Times are correct" resubmits (a real >6h gap is rare but possible).
function tpGapModal(gaps,onConfirm){
  const old=document.getElementById('tp-gap-modal');
  if(old)old.remove();
  const rows=gaps.map(g=>`<li style="margin-bottom:6px"><b>${g.pickupName.startsWith('return_')?'Return trip':'Trip'}</b>: flight ${tpFormat(g.flight)} / pickup ${tpFormat(g.pickup)}</li>`).join('');
  const box=document.createElement('div');
  box.id='tp-gap-modal';
  box.style.cssText='position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px';
  box.innerHTML=`<div role="alertdialog" aria-modal="true" style="background:#fff;color:#222;max-width:440px;width:100%;border-radius:10px;padding:22px;box-shadow:0 10px 30px rgba(0,0,0,.3)">
    <h5 style="margin:0 0 10px;color:#dc3545;font-weight:700">⚠ Please check your times</h5>
    <p style="margin:0 0 10px">Your flight time and pickup time are more than 6 hours apart. AM / PM is probably selected incorrectly.</p>
    <ul style="padding-left:18px;margin:0 0 12px">${rows}</ul>
    <p style="margin:0 0 16px">Please check the times and correct them before submitting.</p>
    <div style="display:flex;flex-direction:column;gap:8px">
      <button type="button" class="tp-gap-fix" style="padding:10px;border:0;border-radius:6px;background:#dc3545;color:#fff;font-weight:600">Correct my times</button>
      <button type="button" class="tp-gap-ok" style="padding:10px;border:1px solid #ccc;border-radius:6px;background:#fff;color:#555">My times are correct, submit</button>
    </div></div>`;
  document.body.appendChild(box);
  box.querySelector('.tp-gap-fix').addEventListener('click',()=>{
    box.remove();
    const wrap=document.getElementById('id_'+gaps[0].pickupName).parentElement;
    wrap.scrollIntoView({behavior:'smooth',block:'center'});
    const hour=wrap.querySelector('.tp-hour');
    if(hour)setTimeout(()=>hour.focus({preventScroll:true}),400);
  });
  box.querySelector('.tp-gap-ok').addEventListener('click',()=>{box.remove();onConfirm();});
}

function flushTimePickers(form){
  (form||document).querySelectorAll('.tp-wrap').forEach(wrap=>{
    if(!wrap._tpUpdate)return;
    const h=wrap.querySelector('.tp-hour').value;
    const m=wrap.querySelector('.tp-min').value;
    if(h||m)wrap._tpUpdate();
  });
}

document.addEventListener('DOMContentLoaded',()=>{
  initTimePickers();
  const dir=document.getElementById('direction');
  if(dir)dir.addEventListener('change',checkFlightPickupGap);  // cruise hides flight time
  document.querySelectorAll('form').forEach(form=>{
    form.addEventListener('submit',e=>{
      flushTimePickers(form);
      const gaps=checkFlightPickupGap();
      const sig=JSON.stringify(gaps);
      if(!gaps.length||form._tpGapConfirmed===sig)return;
      // capture phase on the form runs before the page's own submit handlers,
      // so stopping here keeps the button from flipping to "Submitting..."
      e.preventDefault();
      e.stopImmediatePropagation();
      const submitter=e.submitter;
      tpGapModal(gaps,()=>{
        form._tpGapConfirmed=sig;
        if(form.requestSubmit)form.requestSubmit(submitter&&submitter.form===form?submitter:undefined);
        else form.submit();
      });
    },true);
  });
});
