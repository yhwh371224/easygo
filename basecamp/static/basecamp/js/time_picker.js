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
// picked wrong on one of them — warn under the pickup time (non-blocking).
const TP_GAP_PAIRS=[['flight_time','pickup_time'],['return_flight_time','return_pickup_time']];
const TP_GAP_MAX_MIN=6*60;
function tpMinutes(v){
  const m=/^(\d{2}):(\d{2})$/.exec(v||'');
  return m?parseInt(m[1])*60+parseInt(m[2]):null;
}
function checkFlightPickupGap(){
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
    form.addEventListener('submit',()=>flushTimePickers(form),true);
  });
});
