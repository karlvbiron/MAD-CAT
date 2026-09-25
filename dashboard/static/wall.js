const SERVICES = {
    mongodb:       {name:"MongoDB",       ip:"192.168.1.11:27017", role:"Patient records (system of record)"},
    elasticsearch: {name:"Elasticsearch", ip:"192.168.1.12:9200",  role:"Clinical document search (notes)"},
    cassandra:     {name:"Cassandra",     ip:"192.168.1.13:9042",  role:"IoT vitals stream"},
    redis:         {name:"Redis",         ip:"192.168.1.14:6379",  role:"Active clinical sessions"},
    couchdb:       {name:"CouchDB",       ip:"192.168.1.15:5984",  role:"Patient portal (appointments/refills)"},
    hadoop:        {name:"Hadoop HDFS",   ip:"192.168.1.16:9870",  role:"Billing / compliance archive"},
  };
  const ORDER = ["mongodb","elasticsearch","cassandra","redis","couchdb","hadoop"];
  const RANK = {operational:0, active:1, corrupted:2};
  const PALETTE = {
    operational:{word:"OPERATIONAL", ink:"var(--ok)",   dim:"var(--ok-dim)"},
    active:     {word:"ACTIVE",      ink:"var(--warn)", dim:"var(--warn-dim)"},
    corrupted:  {word:"CORRUPTED",   ink:"var(--bad)",  dim:"var(--bad-dim)"},
  };
  const BREACH_WINDOW_MS = 60*24*3600*1000;   // 60 calendar days (§164.404)
  const MEDIA_THRESHOLD  = 500;               // ≥500 individuals -> HHS + media (§164.408/§164.406)
  
  const state = {};   // svc -> {state, records, lastMsg, at}
  ORDER.forEach(s => state[s] = {state:"operational", records:0, lastMsg:"", at:""});
  let eventCount = 0;
  let discoveryTs = null;   // first corruption observed = breach "discovery"
  
  const $ = id => document.getElementById(id);
  
  // build the six panels
  $("grid").innerHTML = ORDER.map(s => {
    const v = SERVICES[s];
    return `<article data-svc="${s}" class="rounded-xl border hairline overflow-hidden" style="background:var(--panel)">
      <div class="h-1" data-accent style="background:var(--ok)"></div>
      <div class="p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="text-[11px] mono" style="color:var(--muted)">${v.ip}</div>
            <h3 class="text-[16px] font-semibold mt-0.5">${v.name}</h3>
            <p class="text-[12px] mt-0.5" style="color:var(--muted)">${v.role}</p>
          </div>
          <div class="text-right shrink-0">
            <div data-state class="state-readout mono text-[13px] font-medium" style="color:var(--ok)">OPERATIONAL</div>
            <div data-at class="text-[11px] mono mt-1" style="color:var(--muted)">-</div>
          </div>
        </div>
        <div data-box class="mt-3 rounded-lg p-3" style="background:var(--panel-2)">
          <p data-msg class="text-[12.5px] truncate2" style="color:var(--muted)">Nominal, no anomalies.</p>
          <p data-records class="text-[12px] mono mt-1.5" style="color:var(--muted)"></p>
          <p data-safeguard class="text-[11px] mono mt-1.5" style="color:var(--bad);display:none">§164.312(c) Integrity violated</p>
        </div>
      </div>
    </article>`;
  }).join("");
  
  const panelEl = s => document.querySelector(`[data-svc="${s}"]`);
  
  function phaseToState(phase){
    if(phase==="meow") return "corrupted";
    if(["connect","databases","collections","start"].includes(phase)) return "active";
    return null;
  }
  
  function renderPanel(s){
    const st = state[s], p = PALETTE[st.state], el = panelEl(s);
    el.querySelector("[data-state]").textContent = p.word;
    el.querySelector("[data-state]").style.color = p.ink;
    el.querySelector("[data-accent]").style.background = p.ink;
    el.querySelector("[data-box]").style.background = p.dim;
    el.querySelector("[data-at]").textContent = st.at || "-";
    const msg = el.querySelector("[data-msg]");
    msg.textContent = st.state==="operational" ? "Nominal, no anomalies." : (st.lastMsg || "");
    msg.style.color = st.state==="operational" ? "var(--muted)" : "var(--ink)";
    const rec = el.querySelector("[data-records]");
    rec.textContent = st.records>0 ? `${st.records} record${st.records===1?"":"s"} corrupted` : "";
    rec.style.color = st.state==="corrupted" ? "var(--bad)" : "var(--muted)";
    el.querySelector("[data-safeguard]").style.display = st.state==="corrupted" ? "block" : "none";
  }
  
  function pulse(s){
    const el = panelEl(s);
    el.classList.remove("just-changed"); void el.offsetWidth; el.classList.add("just-changed");
  }
  
  function renderCIA(compromised){
    const hit = compromised>0;
    const items = [
      {k:"C", label:"Confidentiality", on:false},
      {k:"I", label:"Integrity",       on:hit},
      {k:"A", label:"Availability",    on:hit},
    ];
    $("cia").innerHTML = items.map(it=>{
      const ink = it.on ? "var(--bad)" : "var(--ok)";
      const dim = it.on ? "var(--bad-dim)" : "var(--ok-dim)";
      const tag = it.on ? "impacted" : (it.k==="C" ? "not read" : "intact");
      return `<div class="flex-1 rounded-lg px-2 py-2 text-center" style="background:${dim}">
        <div class="mono font-medium" style="color:${ink};font-size:18px">${it.k}</div>
        <div class="text-[10px] mt-1" style="color:var(--muted)">${it.label}</div>
        <div class="text-[10px] mono mt-0.5" style="color:${ink}">${tag}</div>
      </div>`;
    }).join("");
  }
  
  function renderSafeguards(compromised){
    const hit = compromised>0;
    const rows = [
      {id:"§164.312(c)(1)", name:"Integrity",      verb:"VIOLATED",   primary:true},
      {id:"§164.312(a)(1)", name:"Access Control", verb:"implicated", primary:false},
      {id:"§164.312(b)",    name:"Audit Controls", verb:"implicated", primary:false},
    ];
    $("safeguards").innerHTML = rows.map(r=>{
      const ink = !hit ? "var(--ok)" : (r.primary ? "var(--bad)" : "var(--warn)");
      const right = !hit ? "ok" : `${r.verb} · ${compromised}/6`;
      return `<div class="flex items-center justify-between gap-2">
        <div class="min-w-0"><span class="mono" style="color:var(--muted)">${r.id}</span> <span>${r.name}</span></div>
        <div class="mono text-[11px] shrink-0" style="color:${ink}">${right}</div>
      </div>`;
    }).join("");
  }
  
  function affectedIndividuals(){
    // Same 25-patient roster flows through all six systems, so distinct
    // individuals affected ≈ the largest single-system record set among the
    // corrupted stores (auto-scales if seeded with more patients).
    return ORDER.reduce((m,s)=> state[s].state==="corrupted" ? Math.max(m, state[s].records) : m, 0);
  }
  
  function renderBreach(){
    const el = $("breach");
    if(!discoveryTs){
      el.innerHTML = `<div class="mono font-medium mt-2" style="color:var(--ok);font-size:20px">no breach detected</div>
        <p class="text-[11px] mt-2" style="color:var(--muted)">clock starts at first corruption (discovery)</p>`;
      return;
    }
    const individuals = affectedIndividuals();
    const over = individuals >= MEDIA_THRESHOLD;
    const deadline = new Date(discoveryTs.getTime() + BREACH_WINDOW_MS);
    el.innerHTML = `
      <div class="mono font-medium mt-2" id="breach-remaining" style="color:var(--warn);font-size:20px">-</div>
      <p class="text-[11px] mt-1" style="color:var(--muted)">until notification deadline · ${deadline.toLocaleDateString()}</p>
      <div class="mt-3 flex items-center justify-between text-[12px]">
        <span style="color:var(--muted)">affected individuals</span>
        <span class="mono" style="color:${over?'var(--bad)':'var(--ink)'}">${individuals}</span>
      </div>
      <p class="text-[11px] mt-2" style="color:${over?'var(--bad)':'var(--muted)'}">
        ${over
          ? "≥ 500: notify HHS + prominent media (HHS breach portal, the \"Wall of Shame\")"
          : "individual notice required within 60 days · below 500, no media/HHS trigger"}</p>`;
    updateClock();
  }
  
  function updateClock(){
    if(!discoveryTs) return;
    const rem = $("breach-remaining");
    if(!rem) return;
    let ms = (discoveryTs.getTime() + BREACH_WINDOW_MS) - Date.now();
    if(ms < 0) ms = 0;
    const d=Math.floor(ms/86400000), h=Math.floor(ms%86400000/3600000),
          m=Math.floor(ms%3600000/60000), s=Math.floor(ms%60000/1000);
    rem.textContent = `${d}d ${String(h).padStart(2,"0")}h ${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
    rem.style.color = "var(--warn)";
  }
  setInterval(updateClock, 1000);
  
  function renderSummary(){
    const phi = ORDER.reduce((n,s)=>n+state[s].records,0);
    const compromised = ORDER.filter(s=>state[s].state==="corrupted").length;
    const active = ORDER.filter(s=>state[s].state==="active").length;
    $("phi").textContent = phi;  $("phi").style.color = phi>0 ? "var(--bad)" : "var(--ok)";
    $("sys").textContent = `${compromised} / 6`;  $("sys").style.color = compromised>0 ? "var(--bad)" : "var(--ok)";
    let word="INTACT", ink="var(--ok)", note="no activity detected";
    if(compromised>0){ word="DEGRADED"; ink="var(--bad)"; note=`${compromised} system${compromised===1?"":"s"} MEOWed`; }
    else if(active>0){ word="PROBING"; ink="var(--warn)"; note="attacker active on the data plane"; }
    $("integrity").textContent = word; $("integrity").style.color = ink;
    $("campaign").textContent = note;
    renderCIA(compromised); renderSafeguards(compromised); renderBreach();
  }
  
  function pushFeed(ev){
    eventCount++; $("count").textContent = `${eventCount} event${eventCount===1?"":"s"}`;
    const t = (ev.ts||"").slice(11,19);
    const colour = ev.phase==="meow" ? "var(--bad)" : ev.phase==="log" ? "var(--muted)" : "var(--warn)";
    const row = document.createElement("div");
    row.className = "whitespace-pre-wrap";
    row.innerHTML =
      `<span style="color:var(--muted)">${t}</span> `+
      `<span style="color:${colour}">${(ev.phase||"log").padEnd(11)}</span>`+
      `<span style="color:var(--muted)">${(ev.service||"-").padEnd(14)}</span>`+
      `<span>${(ev.message||"").replace(/</g,"&lt;")}</span>`;
    const feed = $("feed");
    feed.appendChild(row);
    while(feed.childElementCount>250) feed.removeChild(feed.firstChild);
    feed.scrollTop = feed.scrollHeight;
  }
  
  function handle(ev){
    if(ev.type==="control" && ev.action==="reset") return doReset(false);
    pushFeed(ev);
    const s = ev.service;
    if(!s || !state[s]) { renderSummary(); return; }
    const st = state[s];
  
    if(ev.phase==="meow"){
      if(ev.records_affected!=null) st.records = Math.max(st.records, ev.records_affected);
      else if(/^Modified\b/i.test(ev.message||"")) st.records += 1;
    }
  
    const ns = phaseToState(ev.phase);
    if(ns && RANK[ns] >= RANK[st.state]){
      const changed = RANK[ns] > RANK[st.state];
      if(ns==="corrupted" && !discoveryTs) discoveryTs = new Date();
      st.state = ns; st.at = new Date().toLocaleTimeString(); st.lastMsg = ev.message || st.lastMsg;
      renderPanel(s); if(changed) pulse(s);
    } else if(st.state!=="operational"){
      st.lastMsg = ev.message || st.lastMsg; renderPanel(s);
    } else {
      renderPanel(s);
    }
    renderSummary();
  }
  
  function doReset(alsoServer){
    eventCount=0; $("count").textContent="0 events"; $("feed").innerHTML=""; discoveryTs=null;
    ORDER.forEach(s=>{ state[s]={state:"operational",records:0,lastMsg:"",at:""}; renderPanel(s); });
    renderSummary();
    if(alsoServer) fetch("/reset",{method:"POST"}).catch(()=>{});
  }
  
  $("reset").addEventListener("click", ()=>doReset(true));
  ORDER.forEach(renderPanel); renderSummary();
  
  // SSE
  function connect(){
    const es = new EventSource("/events");
    es.onopen = ()=>{ $("conn").innerHTML = `<span class="inline-block w-2 h-2 rounded-sm" style="background:var(--ok)"></span>connected`; };
    es.onmessage = e=>{ try{ handle(JSON.parse(e.data)); }catch(_){} };
    es.onerror = ()=>{ $("conn").innerHTML = `<span class="inline-block w-2 h-2 rounded-sm" style="background:var(--warn)"></span>reconnecting`; };
  }
  connect();