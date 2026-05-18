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
    const vKey=document.getElementById('ap-vehicle').value;
    const v=vehicleRates[vKey];
    const route=getRouteEstimate(from,to);
    const price=Math.round(v.base+(route.dist*v.perKm));
    document.getElementById('pa-amount').textContent='$'+price;
    document.getElementById('pa-vehicle').textContent=v.name;
    document.getElementById('pa-dist').textContent=route.dist+' km';
    document.getElementById('pa-time').textContent=route.dur;
    document.getElementById('price-airport').style.display='block';
  } else if(type==='hourly'){
    const vKey=document.getElementById('hr-vehicle').value;
    const hours=parseInt(document.getElementById('hr-hours').value);
    const v=vehicleRates[vKey];
    const price=v.hrRate*hours;
    document.getElementById('ph-amount').textContent='$'+price;
    document.getElementById('ph-vehicle').textContent=v.name;
    document.getElementById('ph-hours').textContent=hours+' hours';
    document.getElementById('ph-rate').textContent='$'+v.hrRate+'/hr';
    document.getElementById('price-hourly').style.display='block';
  } else if(type==='wedding'){
    const vKey=document.getElementById('wd-vehicle').value;
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

function openModal(type){
  const modal=document.getElementById('bookingModal');
  if(type==='airport'){
    document.getElementById('modal-title').textContent='Airport Transfer';
    document.getElementById('modal-price').innerHTML=document.getElementById('pa-amount').textContent+' <span>est. fare</span>';
    document.getElementById('md-from').textContent=document.getElementById('ap-from').value||'Sydney Airport';
    document.getElementById('md-to').textContent=document.getElementById('ap-to').value||'Sydney CBD';
    document.getElementById('md-vehicle').textContent=document.getElementById('pa-vehicle').textContent;
  } else if(type==='hourly'){
    document.getElementById('modal-title').textContent='Hourly Hire';
    document.getElementById('modal-price').innerHTML=document.getElementById('ph-amount').textContent+' <span>total fare</span>';
    document.getElementById('md-from').textContent=document.getElementById('hr-from').value||'Sydney CBD';
    document.getElementById('md-to').textContent='As directed';
    document.getElementById('md-vehicle').textContent=document.getElementById('ph-vehicle').textContent;
  } else if(type==='wedding'){
    document.getElementById('modal-title').textContent='Wedding Package';
    document.getElementById('modal-price').innerHTML=document.getElementById('pw-amount').textContent+' <span>package from</span>';
    document.getElementById('md-from').textContent=document.getElementById('wd-loc').value||'Venue TBC';
    document.getElementById('md-to').textContent='Wedding venue';
    document.getElementById('md-vehicle').textContent=document.getElementById('pw-vehicle').textContent;
  } else {
    document.getElementById('modal-title').textContent='Corporate Account';
    document.getElementById('modal-price').innerHTML='Custom <span>pricing</span>';
    document.getElementById('md-from').textContent=document.getElementById('co-company').value||'Your company';
    document.getElementById('md-to').textContent='Multiple locations';
    document.getElementById('md-vehicle').textContent='Fleet assignment';
  }
  modal.classList.add('open');
}

function closeModal(){
  document.getElementById('bookingModal').classList.remove('open');
}

function confirmBooking(){
  closeModal();
  alert('Thank you! Your booking request has been received.\n\nA Black Glide specialist will contact you within 15 minutes to confirm.\n\nFor urgent bookings call: (02) 9XXX XXXX');
}

function callUs(){
  alert('Call us anytime on (02) 9XXX XXXX\nAfter hours: 0400 XXX XXX\n\nWe\'re available 24/7.');
}

function submitEnquiry(){
  alert('Thank you for your enquiry!\n\nOur Sydney team will respond within 30 minutes.\n\nFor urgent bookings: (02) 9XXX XXXX');
}

// Close modal on overlay click
document.getElementById('bookingModal').addEventListener('click',function(e){
  if(e.target===this) closeModal();
});
