(()=>{'use strict';
const c=document.getElementById('game'),g=c.getContext('2d'),panel=document.getElementById('panel'),card=document.getElementById('card');
const hud={level:document.getElementById('level'),army:document.getElementById('army'),coins:document.getElementById('coins')};
let W=0,H=0,dpr=1,run=false,last=0,dist=0,level=1,army=8,coins=0,x=0.5,entities=[],particles=[],spawnAt=0,score=0,drag=false;
try{coins=+(localStorage.getItem('arCoins')||0);level=Math.max(1,+(localStorage.getItem('arLevel')||1))}catch(e){}
const rnd=(a,b)=>a+Math.random()*(b-a),clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function resize(){dpr=Math.min(2,devicePixelRatio||1);W=innerWidth;H=innerHeight;c.width=W*dpr;c.height=H*dpr;g.setTransform(dpr,0,0,dpr,0,0)}addEventListener('resize',resize);resize();
function save(){try{localStorage.setItem('arCoins',coins);localStorage.setItem('arLevel',level)}catch(e){}}
function start(){run=true;dist=0;army=8+Math.floor(level/3);x=.5;entities=[];particles=[];spawnAt=0;score=0;panel.style.display='none';hud.level.textContent='FASE '+level;last=performance.now();requestAnimationFrame(frame)}
function menu(title,msg,button,action){run=false;panel.style.display='flex';card.innerHTML='<h1>'+title+'</h1><p>'+msg+'</p><button id="play">'+button+'</button>';document.getElementById('play').onclick=action}
document.getElementById('play').onclick=start;
function project(lane,z){const t=clamp(z,0,1),persp=.23+.77*(1-t);return {x:W/2+(lane-.5)*W*.85*persp,y:H*.86-t*H*.77,s:persp}}
function spawn(){const gate=Math.random()<.55;const z=1.12;if(gate){const v=Math.random()<.5?'+':'×';entities.push({type:'gate',lane:.27,z,op:v,val:v==='+'?Math.floor(rnd(5,20)):Math.floor(rnd(2,4)),hit:false});entities.push({type:'gate',lane:.73,z,op:Math.random()<.5?'+':'×',val:Math.floor(rnd(2,9)),hit:false})}else{entities.push({type:'enemy',lane:rnd(.2,.8),z,n:Math.floor(rnd(4,11)+level*1.4),hit:false})}}
function burst(px,py,color,n=15){for(let i=0;i<n;i++)particles.push({x:px,y:py,vx:rnd(-130,130),vy:rnd(-200,30),life:rnd(.3,.85),color})}
function finish(win){if(win){coins+=20+Math.floor(army/2);level++;save();menu('VITÓRIA!','Seu exército venceu! Moedas: '+coins,'PRÓXIMA FASE',start)}else{menu('DERROTA','Seu exército foi derrotado. Tente escolher os melhores portões.','TENTAR NOVAMENTE',start)}}
function drawSoldier(px,py,s,col,enemy=false){g.save();g.translate(px,py);g.scale(s,s);g.fillStyle='#0004';g.beginPath();g.ellipse(0,12,13,5,0,0,7);g.fill();g.fillStyle=col;g.fillRect(-8,-9,16,20);g.fillStyle=enemy?'#a52b35':'#b9d7f5';g.beginPath();g.arc(0,-15,9,0,7);g.fill();g.fillStyle=enemy?'#f6b17a':'#ffe4b5';g.fillRect(-5,-19,10,6);g.fillStyle='#d4eaff';g.fillRect(8,-8,3,26);g.fillStyle='#f6c35c';g.fillRect(7,-13,5,7);g.restore()}
function frame(now){if(!run)return;const dt=Math.min(.04,(now-last)/1000||0);last=now;dist+=dt*19;g.clearRect(0,0,W,H);
let sky=g.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#243c6c');sky.addColorStop(1,'#8fd5e8');g.fillStyle=sky;g.fillRect(0,0,W,H);
g.fillStyle='#1c5276';g.fillRect(0,H*.35,W,H*.65);
g.beginPath();g.moveTo(W*.39,H*.1);g.lineTo(W*.61,H*.1);g.lineTo(W*.98,H);g.lineTo(W*.02,H);g.closePath();g.fillStyle='#b8b3a6';g.fill();
g.strokeStyle='#8b8d8b';g.lineWidth=2;for(let i=0;i<13;i++){let t=((i/13+dist*.017)%1),p=project(.5,t);g.beginPath();g.moveTo(W/2-W*.42*p.s,p.y);g.lineTo(W/2+W*.42*p.s,p.y);g.stroke()}
for(const side of [-1,1]){g.strokeStyle='#d0a56c';g.lineWidth=8;g.beginPath();g.moveTo(W/2+side*W*.12,H*.1);g.lineTo(W/2+side*W*.49,H);g.stroke()}
if(dist>spawnAt&&dist<330){spawn();spawnAt=dist+rnd(21,32)}
for(const e of entities){e.z-=dt*.24;const p=project(e.lane,e.z);if(e.z<-.12)continue;
if(e.type==='gate'){const w=54*p.s+24,h=70*p.s+20;g.fillStyle=e.op==='+'?'#1676d9':'#19a769';g.fillRect(p.x-w/2,p.y-h,w,h);g.strokeStyle='#d9f4ff';g.lineWidth=3;g.strokeRect(p.x-w/2,p.y-h,w,h);g.fillStyle='white';g.font='900 '+Math.max(14,29*p.s)+'px system-ui';g.textAlign='center';g.fillText(e.op+e.val,p.x,p.y-h*.37)}
else{const count=Math.min(e.n,15);for(let i=0;i<count;i++)drawSoldier(p.x+((i%5)-2)*13*p.s,p.y-Math.floor(i/5)*17*p.s,Math.max(.24,p.s*.8),'#a9354b',true);g.font='bold 17px system-ui';g.fillStyle='white';g.textAlign='center';g.fillText(e.n,p.x,p.y-42*p.s)}
if(!e.hit&&e.z<.19&&e.z>-.03&&Math.abs(e.lane-x)<.24){e.hit=true;if(e.type==='gate'){army=e.op==='+'?army+e.val:army*e.val;army=Math.min(220,army);burst(p.x,p.y,'#ffe56b',22)}else{army=Math.max(0,army-e.n);burst(p.x,p.y,'#f76b61',22);if(army<=0){finish(false);return}}}}
entities=entities.filter(e=>e.z>-.14);
const player=project(x,.02);const count=Math.min(army,80),cols=Math.max(3,Math.ceil(Math.sqrt(count*1.6)));for(let i=count-1;i>=0;i--){const row=Math.floor(i/cols),col=i%cols;drawSoldier(player.x+(col-(cols-1)/2)*Math.min(20,W*.72/cols),H*.82-row*17,Math.min(1,W/420),'#2678da')}
for(const p of particles){p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=260*dt;p.life-=dt;g.globalAlpha=clamp(p.life*2,0,1);g.fillStyle=p.color;g.fillRect(p.x,p.y,5,5)}g.globalAlpha=1;particles=particles.filter(p=>p.life>0);
hud.army.textContent='⚔ '+army;hud.coins.textContent='🪙 '+coins;
g.fillStyle='#0006';g.fillRect(W*.12,H*.075,W*.76,8);g.fillStyle='#ffd35e';g.fillRect(W*.12,H*.075,W*.76*clamp(dist/350,0,1),8);
if(dist>350){finish(true);return}requestAnimationFrame(frame)}
function move(e){if(!drag||!run)return;x=clamp(e.clientX/W,.13,.87)}c.addEventListener('pointerdown',e=>{drag=true;move(e)});c.addEventListener('pointermove',move);addEventListener('pointerup',()=>drag=false);
window.pauseGame=()=>{if(run)menu('PAUSADO','Fase '+level+' — continue sua batalha.','CONTINUAR',()=>{panel.style.display='none';run=true;last=performance.now();requestAnimationFrame(frame)})};
})();