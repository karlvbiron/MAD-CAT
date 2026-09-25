(function(){
  const $ = id => document.getElementById(id);

  // Shared namespace + tiny pub/sub bus, used by incidents.js / reports.js
  // (this is the first feature script to load, so it initialises it).
  window.MADCAT = window.MADCAT || {};
  window.MADCAT._subs = window.MADCAT._subs || {};
  window.MADCAT.on = window.MADCAT.on || function(evt, fn){ (window.MADCAT._subs[evt] || (window.MADCAT._subs[evt] = [])).push(fn); };
  window.MADCAT.emit = window.MADCAT.emit || function(evt){ (window.MADCAT._subs[evt] || []).forEach(function(fn){ try{ fn(); }catch(_){} }); };
  // Transient toast notifications. Suppressed while the SSO gate is up.
  window.MADCAT.toast = window.MADCAT.toast || function(title, opts){
    opts = opts || {};
    const gate = document.getElementById("sso-gate");
    if(gate && getComputedStyle(gate).display !== "none") return;
    const c = document.getElementById("toast-container");
    if(!c) return;
    const esc = function(s){ return String(s == null ? "" : s).replace(/[&<>]/g, function(m){ return { "&":"&amp;","<":"&lt;",">":"&gt;" }[m]; }); };
    const el = document.createElement("div");
    el.className = "toast toast-" + (opts.type || "info");
    el.innerHTML = '<div class="toast-title">' + esc(title) + '</div>' +
                   (opts.msg ? '<div class="toast-msg">' + esc(opts.msg) + '</div>' : '');
    c.appendChild(el);
    setTimeout(function(){
      el.style.transition = "opacity .3s"; el.style.opacity = "0";
      setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); }, 300);
    }, opts.ttl || 4200);
  };

  // Safeguard model. Weights of impacted cells sum to 55 -> score floor 45 at 6/6.
  const FAMILIES = [
    { code:"§164.308", name:"Administrative Safeguards", cells:[
      { id:"§164.308(a)(1)(ii)(A)", name:"Risk Analysis",                 impact:"implicated", weight:2 },
      { id:"§164.308(a)(6)",        name:"Security Incident Procedures",  impact:"implicated", weight:2 },
      { id:"§164.308(a)(7)(i)",     name:"Contingency Plan",              impact:"implicated", weight:2 },
      { id:"§164.308(a)(5)",        name:"Security Awareness & Training",  impact:"ok",        weight:0 },
      { id:"§164.308(a)(3)",        name:"Workforce Security",             impact:"ok",        weight:0 },
    ]},
    { code:"§164.310", name:"Physical Safeguards", cells:[
      { id:"§164.310(a)(1)", name:"Facility Access Controls", impact:"ok", weight:0 },
      { id:"§164.310(c)",    name:"Workstation Security",     impact:"ok", weight:0 },
      { id:"§164.310(d)(1)", name:"Device & Media Controls",  impact:"ok", weight:0 },
    ]},
    { code:"§164.312", name:"Technical Safeguards", cells:[
      { id:"§164.312(c)(1)",     name:"Integrity",               impact:"violated",   weight:40 },
      { id:"§164.312(a)(1)",     name:"Access Control",          impact:"implicated", weight:5 },
      { id:"§164.312(b)",        name:"Audit Controls",          impact:"implicated", weight:4 },
      { id:"§164.312(a)(2)(iv)", name:"Encryption & Decryption", impact:"ok",         weight:0 },
      { id:"§164.312(e)(1)",     name:"Transmission Security",   impact:"ok",         weight:0 },
    ]},
  ];

  // HIPAA -> NIST crosswalk (per SP 800-66 Rev. 2 -> CSF 2.0 / SP 800-53 Rev. 5).
  const CROSSWALK = [
    { id:"§164.312(c)(1)",        name:"Integrity",                    csf:"PR.DS-06",         sp:"SI-7",        impact:"violated" },
    { id:"§164.312(a)(1)",        name:"Access Control",               csf:"PR.AA",            sp:"AC-3, AC-6",  impact:"implicated" },
    { id:"§164.312(b)",           name:"Audit Controls",               csf:"PR.PS-04 / DE.CM", sp:"AU-2, AU-6",  impact:"implicated" },
    { id:"§164.308(a)(1)(ii)(A)", name:"Risk Analysis",                csf:"ID.RA",            sp:"RA-3",        impact:"implicated" },
    { id:"§164.308(a)(7)(i)",     name:"Contingency Plan",             csf:"RC.RP / PR.DS-11", sp:"CP-9, CP-10", impact:"implicated" },
    { id:"§164.308(a)(6)",        name:"Security Incident Procedures", csf:"RS.MA / RS.AN",    sp:"IR-4, IR-8",  impact:"implicated" },
  ];

  const STYLE = {
    violated:  {ink:"var(--bad)",  tint:"var(--bad-dim)",  label:"Violated"},
    implicated:{ink:"var(--warn)", tint:"var(--warn-dim)", label:"Implicated"},
    ok:        {ink:"var(--ok)",   tint:"var(--ok-dim)",   label:"Compliant"},
  };

  const corruptedCount = () => ORDER.filter(s => state[s].state === "corrupted").length;

  function renderScore(c, total, score, status, sty){
    $("h-score").textContent = score;
    $("h-score").style.color = sty.ink;
    $("h-score-bar").style.width = score + "%";
    $("h-score-bar").style.background = sty.ink;
    const st = $("h-status");
    st.textContent = status; st.style.color = sty.ink; st.style.background = sty.tint;
    $("h-score-note").textContent = c === 0
      ? "All safeguards operating. No integrity events on the data plane."
      : `Integrity safeguard violated across ${c} of 6 systems: ${total} points deducted from the Security Rule safeguards a Meow attack degrades.`;

    const impacted = [];
    FAMILIES.forEach(f => f.cells.forEach(cell => { if(cell._ded > 0) impacted.push(cell); }));
    impacted.sort((a,b) => b._ded - a._ded);
    $("h-contrib").innerHTML = c === 0 ? "" :
      `<div class="text-[11px] mb-1.5 mt-3" style="color:var(--muted)">What's reducing the score</div>` +
      impacted.slice(0, 8).map(cell => {
        const s = STYLE[cell.impact];
        return `<div class="flex items-center justify-between text-[12px] py-0.5">
          <span>${cell.name}</span><span class="mono" style="color:${s.ink}">-${cell._ded}</span></div>`;
      }).join("");
  }

  function renderHeatmap(c){
    $("h-heatmap").innerHTML = FAMILIES.map(fam => {
      const cells = fam.cells.map(cell => {
        const impacted = c > 0 && cell.impact !== "ok";
        const s = STYLE[impacted ? cell.impact : "ok"];
        return `<div class="hx-cell" style="background:${s.tint}">
          <div class="min-w-0">
            <div class="mono text-[10.5px]" style="color:var(--muted)">${cell.id}</div>
            <div class="text-[12.5px] leading-tight">${cell.name}</div>
          </div>
          <div class="text-right shrink-0">
            <div class="text-[11px] font-medium" style="color:${s.ink}">${s.label}</div>
            ${cell._ded > 0 ? `<div class="mono text-[10.5px]" style="color:${s.ink}">-${cell._ded}</div>` : ``}
          </div>
        </div>`;
      }).join("");
      return `<div class="card rounded-xl p-4">
        <div class="hx-fam-title">${fam.name}</div>
        <div class="hx-fam-sub">${fam.code}</div>
        <div class="mt-3 space-y-1.5">${cells}</div>
      </div>`;
    }).join("");
  }

  function renderCIA(c){
    const hit = c > 0;
    const items = [
      {k:"C", label:"Confidentiality", on:false},
      {k:"I", label:"Integrity",       on:hit},
      {k:"A", label:"Availability",    on:hit},
    ];
    $("h-cia").innerHTML = items.map(it => {
      const ink = it.on ? "var(--bad)" : "var(--ok)";
      const dim = it.on ? "var(--bad-dim)" : "var(--ok-dim)";
      const tag = it.on ? "impacted" : (it.k === "C" ? "not read" : "intact");
      return `<div class="flex-1 rounded-lg px-2 py-2 text-center" style="background:${dim}">
        <div class="mono font-medium" style="color:${ink};font-size:18px">${it.k}</div>
        <div class="text-[10px] mt-1" style="color:var(--muted)">${it.label}</div>
        <div class="text-[10px] mono mt-0.5" style="color:${ink}">${tag}</div>
      </div>`;
    }).join("");
  }

  function renderBreach(){
    const el = $("h-breach");
    if(!discoveryTs){
      el.innerHTML = `<div class="mono font-medium mt-2" style="color:var(--ok);font-size:20px">No reportable breach</div>
        <p class="text-[11px] mt-2" style="color:var(--muted)">The 60-day notification clock starts at first corruption (discovery).</p>`;
      return;
    }
    const individuals = affectedIndividuals();
    const over = individuals >= MEDIA_THRESHOLD;
    const deadline = new Date(discoveryTs.getTime() + BREACH_WINDOW_MS);
    el.innerHTML = `
      <div class="flex items-baseline justify-between mt-2">
        <div class="mono font-medium" id="h-breach-clock" style="font-size:22px;color:var(--warn)">-</div>
        <div class="text-[11px]" style="color:var(--muted)">deadline ${deadline.toLocaleDateString()}</div>
      </div>
      <div class="h-bar mt-3"><div id="h-breach-bar" class="h-bar-fill" style="width:0%;background:var(--warn)"></div></div>
      <div class="mt-3 grid grid-cols-2 gap-3 text-[12px]">
        <div><div class="text-[11px]" style="color:var(--muted)">Discovered</div><div class="mono">${discoveryTs.toLocaleString()}</div></div>
        <div><div class="text-[11px]" style="color:var(--muted)">Affected individuals</div><div class="mono" style="color:${over?'var(--bad)':'var(--ink)'}">${individuals}</div></div>
      </div>
      <p class="text-[11px] mt-3" style="color:${over?'var(--bad)':'var(--muted)'}">${over
        ? "\u2265 500 individuals, notify HHS and prominent media without unreasonable delay (HHS breach portal, the \"Wall of Shame\")."
        : "Below 500 individuals, individual notice within 60 days; HHS via the annual log."}</p>`;
    updateClock();
  }

  function updateClock(){
    const rem = $("h-breach-clock");
    if(!rem || !discoveryTs) return;
    const total = BREACH_WINDOW_MS;
    let ms = (discoveryTs.getTime() + total) - Date.now();
    const overdue = ms <= 0;
    if(ms < 0) ms = 0;
    const d = Math.floor(ms/86400000), h = Math.floor(ms%86400000/3600000),
          m = Math.floor(ms%3600000/60000), s = Math.floor(ms%60000/1000);
    rem.textContent = overdue ? "Notification overdue"
      : `${d}d ${String(h).padStart(2,"0")}h ${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
    const col = (overdue || ms/86400000 <= 7) ? "var(--bad)" : "var(--warn)";
    rem.style.color = col;
    const bar = $("h-breach-bar");
    if(bar){ bar.style.width = (Math.min(total-ms,total)/total*100).toFixed(1) + "%"; bar.style.background = col; }
  }

  function renderActions(){
    const el = $("h-actions");
    if(!discoveryTs){
      el.innerHTML = `<p class="text-[12px]" style="color:var(--muted)">No actions required - no reportable breach.</p>`;
      return;
    }
    const over = affectedIndividuals() >= MEDIA_THRESHOLD;
    const LV = {
      required:   {ink:"var(--bad)",   tint:"var(--bad-dim)",  label:"Required"},
      conditional:{ink:"var(--warn)",  tint:"var(--warn-dim)", label:"Conditional"},
      assess:     {ink:"var(--warn)",  tint:"var(--warn-dim)", label:"Assess"},
      muted:      {ink:"var(--muted)", tint:"var(--panel-2)",  label:"Not triggered"},
    };
    const rows = [
      {t:"Notify affected individuals", d:"Written notice without unreasonable delay, no later than 60 days from discovery.", lv:"required"},
      {t:"Notify HHS Secretary", d: over ? "\u2265 500, notify without unreasonable delay, within 60 days." : "< 500, record in the annual log filed with HHS.", lv: over ? "required" : "conditional"},
      {t:"Notify prominent media", d: over ? "Required for \u2265 500 individuals in a state or jurisdiction." : "Not triggered below 500 individuals.", lv: over ? "required" : "muted"},
      {t:"Complete four-factor Breach Risk Assessment", d:"Assess the probability that PHI was compromised. A Meow attack corrupts rather than reads, so factor 3 (whether PHI was actually acquired or viewed) is ambiguous; integrity and availability loss still require the assessment.", lv:"assess"},
    ];
    el.innerHTML = rows.map(r => {
      const s = LV[r.lv];
      return `<div class="flex gap-2.5">
        <span class="shrink-0 mt-1.5 inline-block w-2 h-2 rounded-sm" style="background:${s.ink}"></span>
        <div class="min-w-0">
          <div class="text-[12.5px] font-medium flex items-center gap-2">${r.t}
            <span class="chip" style="color:${s.ink};background:${s.tint}">${s.label}</span></div>
          <div class="text-[11.5px] mt-0.5" style="color:var(--muted)">${r.d}</div>
        </div></div>`;
    }).join("");
  }

  function renderCrosswalk(c){
    const head = `<thead><tr>
      <th>HIPAA §</th><th>Safeguard</th><th>NIST CSF 2.0</th><th>SP 800-53 Rev. 5</th><th>Status</th>
    </tr></thead>`;
    const body = CROSSWALK.map(r => {
      const s = STYLE[c > 0 ? r.impact : "ok"];
      const bg = c > 0 ? s.tint : "transparent";
      return `<tr>
        <td class="mono" style="white-space:nowrap;color:var(--muted);background:${bg}">${r.id}</td>
        <td style="background:${bg}">${r.name}</td>
        <td class="mono" style="background:${bg}">${r.csf}</td>
        <td class="mono" style="background:${bg}">${r.sp}</td>
        <td style="background:${bg};color:${s.ink};font-weight:600;white-space:nowrap">${s.label}</td>
      </tr>`;
    }).join("");
    $("h-crosswalk").innerHTML = head + `<tbody>${body}</tbody>`;
  }

  // Publish the derived compliance posture so incidents.js can snapshot it at
  // peak and reports.js can render a faithful, self-contained report.
  function publishSnapshot(c, total, score, status){
    window.MADCAT.compliance = {
      c: c, total: total, score: score, status: status,
      families: FAMILIES.map(function(fam){ return {
        code: fam.code, name: fam.name,
        cells: fam.cells.map(function(cl){ return {
          id: cl.id, name: cl.name,
          impact: (c > 0 && cl.impact !== "ok") ? cl.impact : "ok",
          ded: cl._ded || 0,
        }; }),
      }; }),
      crosswalk: CROSSWALK.map(function(r){ return {
        id: r.id, name: r.name, csf: r.csf, sp: r.sp,
        impact: (c > 0) ? r.impact : "ok",
      }; }),
      cia: { C: false, I: c > 0, A: c > 0 },
      breach: discoveryTs ? {
        discoveredAt: discoveryTs.toISOString(),
        individuals: affectedIndividuals(),
        over: affectedIndividuals() >= MEDIA_THRESHOLD,
        deadline: new Date(discoveryTs.getTime() + BREACH_WINDOW_MS).toISOString(),
      } : null,
    };
    window.MADCAT.emit("compliance");
  }

  function renderHipaa(){
    const c = corruptedCount();
    const f = c/6;
    let total = 0;
    FAMILIES.forEach(fam => fam.cells.forEach(cell => {
      cell._ded = (c > 0 && cell.impact !== "ok") ? Math.round(cell.weight * f) : 0;
      total += cell._ded;
    }));
    const score = 100 - total;
    let status, sty;
    if(c === 0){ status = "Compliant"; sty = STYLE.ok; }
    else if(score >= 60){ status = "At risk"; sty = STYLE.implicated; }
    else { status = "Non-compliant"; sty = STYLE.violated; }
    renderScore(c, total, score, status, sty);
    renderHeatmap(c);
    renderCIA(c);
    renderBreach();
    renderActions();
    renderCrosswalk(c);
    publishSnapshot(c, total, score, status);
  }

  // Wrap the wall's renderSummary so every live update + restore refreshes these
  // derived views without affecting the attack visualization. Errors are contained.
  if(typeof renderSummary === "function"){
    const _rs = renderSummary;
    window.renderSummary = function(){
      _rs.apply(this, arguments);
      try{ renderHipaa(); }catch(e){ }
    };
  }
  setInterval(updateClock, 1000);
  renderHipaa();
})();