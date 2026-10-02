const tg=window.Telegram.WebApp;tg.ready();tg.expand();
const initData=tg.initData;
let me=null;

async function request(path,method="POST"){
 const r=await fetch(path,{method,headers:{"Content-Type":"application/json"},body:method==="POST"?JSON.stringify({init_data:initData}):undefined});
 const d=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(d.detail||"Request failed");return d;
}
function render(){
 document.querySelector("#user").textContent=`👤 ${me.first_name||me.username||"User"}`;
 document.querySelector("#balance").textContent=me.balance;
 document.querySelector("#refs").textContent=me.referrals;
}
async function load(){
 if(!initData){document.querySelector("#user").textContent="Open Profit AI inside Telegram.";return}
 try{me=await request("/api/me");render()}catch(e){tg.showAlert(e.message)}
}
document.querySelector("#daily").onclick=async()=>{try{const d=await request("/api/daily");me.balance=d.balance;render();tg.showAlert("🎁 +100 points added!")}catch(e){tg.showAlert(e.message)}};
document.querySelector("#invite").onclick=()=>{
 const bot="YOUR_BOT_USERNAME";
 const link=`https://t.me/${bot}?startapp=${me.id}`;
 tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent("Join Profit AI 🚀")}`);
};
document.querySelector("#board").onclick=async()=>{
 const box=document.querySelector("#leaders");box.classList.toggle("hidden");if(box.classList.contains("hidden"))return;
 const rows=await request("/api/leaderboard","GET");
 document.querySelector("#rows").innerHTML=rows.map((r,i)=>`<div class="row"><span class="rank">${i+1}</span><span class="name">${safe(r.first_name||r.username||"User")}</span><span class="points">${r.balance}</span></div>`).join("");
};
function safe(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
load();
