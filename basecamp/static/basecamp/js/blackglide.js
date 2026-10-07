// Hero image ken-burns effect
window.addEventListener('load',function(){
  var img=document.getElementById('heroImg');
  if(img) setTimeout(function(){img.classList.add('loaded');},100);
});

// Tab switching
function switchTab(tab){
  document.querySelectorAll('.btab').forEach((b,i)=>{
    const tabs=['airport','hourly','wedding','corporate'];
    b.classList.toggle('active',tabs[i]===tab);
  });
  document.querySelectorAll('.bform').forEach(f=>f.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
}

// Price data
const vehicleRates={
  sedan:{name:'Business Sedan',base:95,perKm:2.2,hrRate:95},
  luxury:{name:'S-Class Sedan',base:145,perKm:3.1,hrRate:145},
  suv:{name:'Premium SUV',base:125,perKm:2.7,hrRate:125},
  van:{name:'People Mover',base:155,perKm:3.0,hrRate:155},
  limo:{name:'Stretch Limousine',base:280,perKm:4.5,hrRate:280}
};

// The form asks for passengers, not vehicle class — pick the vehicle that fits.
function vehicleForPax(pax){
  if(pax<=3) return 'sedan';
  if(pax<=6) return 'suv';
  return 'van';
}

function weddingVehicleForPax(pax){
  if(pax<=4) return 'luxury';
  if(pax<=7) return 'van';
  return 'limo';
}

function getRouteEstimate(from,to){
  const toLC=to.toLowerCase();
  if(toLC.includes('cbd')||toLC.includes('city')||toLC.includes('circular')||toLC.includes('darling')) return {dist:15,dur:'25 min'};
  if(toLC.includes('bondi')||toLC.includes('eastern')) return {dist:18,dur:'30 min'};
  if(toLC.includes('north sydney')||toLC.includes('north shore')) return {dist:22,dur:'35 min'};
  if(toLC.includes('manly')||toLC.includes('northern beach')) return {dist:28,dur:'45 min'};
  if(toLC.includes('parramatta')||toLC.includes('western')) return {dist:32,dur:'50 min'};
  if(toLC.includes('hunter')||toLC.includes('newcastle')) return {dist:165,dur:'2 hr 10 min'};
  if(toLC.includes('blue mountain')) return {dist:105,dur:'1 hr 30 min'};
  return {dist:20,dur:'30 min'};
}

function calcPrice(type){
  if(type==='airport'){
    const from=document.getElementById('ap-from').value||'Sydney Airport';
    const to=document.getElementById('ap-to').value||'Sydney CBD';
    const pax=parseInt(document.getElementById('ap-pax').value);
    const v=vehicleRates[vehicleForPax(pax)];
    const route=getRouteEstimate(from,to);
    const price=Math.round(v.base+(route.dist*v.perKm));
    document.getElementById('pa-amount').textContent='$'+price;
    document.getElementById('pa-vehicle').textContent=v.name;
    document.getElementById('pa-dist').textContent=route.dist+' km';
    document.getElementById('pa-time').textContent=route.dur;
    document.getElementById('price-airport').style.display='block';
  } else if(type==='hourly'){
    const pax=parseInt(document.getElementById('hr-pax').value);
    const vKey=vehicleForPax(pax);
    const hours=parseInt(document.getElementById('hr-hours').value);
    const v=vehicleRates[vKey];
    const price=v.hrRate*hours;
    document.getElementById('ph-amount').textContent='$'+price;
    document.getElementById('ph-vehicle').textContent=v.name;
    document.getElementById('ph-hours').textContent=hours+' hours';
    document.getElementById('ph-rate').textContent='$'+v.hrRate+'/hr';
    document.getElementById('price-hourly').style.display='block';
  } else if(type==='wedding'){
    const vKey=weddingVehicleForPax(parseInt(document.getElementById('wd-pax').value));
    const hours=parseInt(document.getElementById('wd-hours').value);
    const weddingRates={limo:280,luxury:175,suv:150,van:195};
    const vNames={limo:'Stretch Limousine',luxury:'S-Class Sedan',suv:'Premium SUV',van:'Bridal Party Van'};
    const price=weddingRates[vKey]*hours;
    document.getElementById('pw-amount').textContent='$'+price;
    document.getElementById('pw-vehicle').textContent=vNames[vKey];
    document.getElementById('pw-hours').textContent=hours+' hours';
    document.getElementById('price-wedding').style.display='block';
  } else if(type==='corporate'){
    const vol=document.getElementById('co-volume').value;
    const discounts={'1-5':'Standard rates apply','5-20':'5% volume discount','20-50':'10% volume discount','50+':'15%+ custom pricing'};
    document.getElementById('pc-msg').textContent=discounts[vol];
    document.getElementById('price-corporate').style.display='block';
  }
}

// All booking actions hand off to the real Black Glide inquiry form, which
// prefills pickup / dropoff / date / passengers from the query string.
const BG_URL='https://blackglide.com.au';
const BG_PHONE='1300253300';

function goInquiry(pickup,dropoff,date,passengers){
  const params=new URLSearchParams();
  if(pickup) params.set('pickup',pickup);
  if(dropoff) params.set('dropoff',dropoff);
  if(date) params.set('date',date.slice(0,10));
  if(passengers) params.set('passengers',passengers);
  const qs=params.toString();
  window.location.href=BG_URL+'/inquiry/'+(qs?'?'+qs:'');
}

function val(id){
  const el=document.getElementById(id);
  return el?el.value.trim():'';
}

function bookOnline(type){
  if(type==='airport') goInquiry(val('ap-from'),val('ap-to'),val('ap-date'),val('ap-pax'));
  else if(type==='hourly') goInquiry(val('hr-from'),'','',val('hr-pax'));
  else if(type==='wedding') goInquiry(val('wd-loc'),'',val('wd-date'),val('wd-pax'));
  else window.location.href=BG_URL+'/contact/';
}

function callUs(){
  window.location.href='tel:'+BG_PHONE;
}

function submitEnquiry(){
  goInquiry(val('bg-pickup'),val('bg-dropoff'),val('bg-date'));
}

// No pickups at midnight — auto-correct 00:00 to 12:00 PM (noon)
(function(){
  const timeInput=document.getElementById('bg-pickup-time');
  const note=document.getElementById('bg-midnight-note');
  if(!timeInput||!note) return;
  timeInput.addEventListener('change',function(){
    const parts=this.value.split(':');
    const hh=parseInt(parts[0],10);
    if(hh===0){
      this.value='12'+this.value.slice(2);
      note.style.display='block';
      clearTimeout(timeInput._noteTimer);
      timeInput._noteTimer=setTimeout(()=>{note.style.display='none';},4000);
    }
  });
})();
