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
      const ampm=wrap.querySelector('.tp-ampm.tp-active').dataset.val;
      h=Math.min(12,Math.max(1,h));
      m=Math.min(59,Math.max(0,m));
      if(ampm==='AM'&&h===12)h=0;
      else if(ampm==='PM'&&h!==12)h+=12;
      hidden.value=`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
    }
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
document.addEventListener('DOMContentLoaded',()=>initTimePickers());