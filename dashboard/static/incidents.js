/* ============================================================
   Incidents.
   An incident case is DERIVED from the wall's live global state:
     Open       -> first corruption event (discoveryTs is set)
     Contained  -> attacker activity goes quiet, or analyst marks it
     Recovered  -> the restore/reset arrives and the wall clears
   The dashboard never drives the lab: response actions only
   annotate the incident timeline. A numbered ledger persists to
   localStorage. Chains onto renderSummary (after hipaa.js) so it
   ticks per event; errors here never reach the wall.
   ============================================================ */
   (function(){
    const $ = id => document.getElementById(id);
    const QUIET_MS = 6000;   // no new corruption for this long -> auto-contained
  
    // ---- persistence ----------------------------------------------------------
    function load(){ try{ return JSON.parse(localStorage.getItem("madcat.incidents") || "[]"); }catch(e){ return []; } }
    function save(){ try{ localStorage.setItem("madcat.incidents", JSON.stringify(registry.ledger)); }catch(e){} }
    function nextId(){
      let n = 0;
      try{ n = parseInt(localStorage.getItem("madcat.seq") || "0", 10) || 0; }catch(e){}
      n += 1;
      try{ localStorage.setItem("madcat.seq", String(n)); }catch(e){}
      return "INC-" + String(n).padStart(4, "0");
    }
  
    // ---- shared registry (read by reports.js) ---------------------------------
    const registry = window.MADCAT.incidents = {
      current: null,
      ledger: load(),
      selectedId: null,
      all(){ return (this.current ? [this.current] : []).concat(this.ledger); },
      get(id){ return this.all().filter(function(x){ return x.id === id; })[0] || null; },
      subject(){ return this.get(this.selectedId) || this.current || this.ledger[0] || null; },
      select(id){ this.selectedId = id; window.MADCAT.emit("incidents"); },
    };
    if(registry.ledger.length) registry.selectedId = registry.ledger[0].id;
  
    // ---- time helpers (also exposed for reports.js) ---------------------------
    function two(n){ return String(n).padStart(2, "0"); }
    function durFromSecs(s){
      if(s < 60) return s + "s";
      const m = Math.floor(s/60), sec = s%60;
      if(m < 60) return m + "m " + two(sec) + "s";
      const h = Math.floor(m/60), mm = m%60;
      return h + "h " + two(mm) + "m";
    }
    function fmtTime(iso){ try{ return new Date(iso).toLocaleString(); }catch(e){ return iso; } }
    function durText(a, b){ return durFromSecs(Math.max(0, Math.floor((new Date(b) - new Date(a))/1000))); }
    function relAgo(ms){ return durFromSecs(Math.max(0, Math.floor((Date.now() - ms)/1000))) + " ago"; }
    window.MADCAT.util = { two: two, durFromSecs: durFromSecs, fmtTime: fmtTime, durText: durText };
  
    // ---- derivation from live wall state --------------------------------------
    function corruptedCount(){ return ORDER.filter(function(s){ return state[s].state === "corrupted"; }).length; }
    function totalRecords(){ return ORDER.reduce(function(n, s){ return n + state[s].records; }, 0); }
  
    let lastSig = "";
    let lastActivity = Date.now();
    let sysSeen = {};
  
    function addTL(inc, kind, text){ inc.timeline.push({ ts: new Date().toISOString(), kind: kind, text: text }); }
    function audit(category, action, opts){ if(window.MADCAT.audit) window.MADCAT.audit.log(category, action, opts); }
    function toast(title, opts){ if(window.MADCAT.toast) window.MADCAT.toast(title, opts); }
  
    function openIncident(when){
      const inc = {
        id: nextId(),
        status: "open",
        openedAt: when.toISOString(),
        containedAt: null,
        recoveredAt: null,
        peakSystems: 0,
        peakRecords: 0,
        affected: {},           // svc -> peak records corrupted
        alertReason: "Anomalous bulk write volume detected on the data plane.",
        compliance: null,       // HIPAA posture snapshot at peak (from hipaa.js)
        timeline: [],
      };
      registry.current = inc;
      sysSeen = {};
      lastActivity = Date.now();
      addTL(inc, "system", "Integrity anomaly detected on the data plane; incident opened.");
      audit("incident", "Incident " + inc.id + " opened", { actor: "Detection engine", detail: inc.alertReason, ref: inc.id });
      toast("Anomalous bulk write volume detected", { type: "alert", msg: "Incident " + inc.id + " opened" });
      accumulate();
    }
  
    function accumulate(){
      const inc = registry.current;
      if(!inc || inc.status === "recovered") return;
      const c = corruptedCount();
      ORDER.forEach(function(s){
        if(state[s].state === "corrupted"){
          const recs = state[s].records;
          if(!sysSeen[s]){
            sysSeen[s] = true;
            addTL(inc, "system", "Bulk overwrite detected on " + SERVICES[s].name + ".");
          }
          inc.affected[s] = Math.max(inc.affected[s] || 0, recs);
        }
      });
      if(c > inc.peakSystems) inc.peakSystems = c;
      const recs = totalRecords();
      if(recs > inc.peakRecords) inc.peakRecords = recs;
      if(c > 0){
        inc.alertReason = "Anomalous bulk write volume across " + c + " system" + (c === 1 ? "" : "s") +
                          "; record values overwritten with non-conforming tokens.";
      }
      // snapshot the derived HIPAA posture at the current (worsening) peak
      if(window.MADCAT.compliance){
        try{ inc.compliance = JSON.parse(JSON.stringify(window.MADCAT.compliance)); }catch(e){}
      }
    }
  
    function contain(auto){
      const inc = registry.current;
      if(!inc || inc.status !== "open") return;
      inc.status = "contained";
      inc.containedAt = new Date().toISOString();
      addTL(inc, auto ? "auto" : "analyst", auto
        ? "Attacker activity subsided; no new corruption observed; incident auto-contained."
        : "Incident marked contained by analyst.");
      audit(auto ? "incident" : "response",
        auto ? ("Incident " + inc.id + " auto-contained") : ("Marked incident " + inc.id + " contained"),
        auto ? { actor: "Detection engine", ref: inc.id } : { ref: inc.id });
      toast("Incident " + inc.id + " contained", { type: "info", msg: auto ? "Attacker activity subsided" : "Marked contained by analyst" });
      save();
      emitAll();
    }
  
    function recover(when){
      const inc = registry.current;
      if(!inc) return;
      inc.status = "recovered";
      inc.recoveredAt = when.toISOString();
      if(!inc.containedAt){ inc.containedAt = when.toISOString(); }
      addTL(inc, "system", "Systems returned to operational; integrity wall cleared.");
      audit("incident", "Incident " + inc.id + " recovered", { actor: "System", detail: "Systems returned to operational; integrity wall cleared.", ref: inc.id });
      toast("Incident " + inc.id + " recovered", { type: "success", msg: "Systems restored to operational" });
      registry.ledger.unshift(inc);
      registry.selectedId = inc.id;   // default the report to the freshest incident
      registry.current = null;
      save();
      emitAll();
    }
  
    function action(kind){
      const inc = registry.current;
      if(!inc) return;
      if(window.MADCAT.session && window.MADCAT.session.isReadOnly && window.MADCAT.session.isReadOnly()) return;
      if(kind === "contain") return contain(false);
      if(kind === "ack")      { addTL(inc, "analyst", "Analyst acknowledged the alert."); audit("response", "Acknowledged incident " + inc.id, { ref: inc.id }); toast("Alert acknowledged", { type: "info", msg: inc.id }); }
      if(kind === "restore")  { addTL(inc, "analyst", "Analyst initiated data restoration (restore_data.py)."); audit("response", "Logged data restoration initiated", { ref: inc.id }); toast("Restoration logged", { type: "info", msg: "Run restore_data.py to recover" }); }
      if(kind === "notify")   { addTL(inc, "analyst", "Privacy officer notified of a suspected breach."); audit("response", "Notified privacy officer", { ref: inc.id }); toast("Privacy officer notified", { type: "info", msg: inc.id }); }
      save();
      emitAll();
    }
  
    function tick(){
      const sig = ORDER.map(function(s){ return state[s].state + ":" + state[s].records; }).join(",");
      if(sig !== lastSig){ lastSig = sig; lastActivity = Date.now(); }
  
      if(!registry.current && discoveryTs){ openIncident(new Date()); emitAll(); return; }
      if(registry.current && registry.current.status !== "recovered"){
        if(discoveryTs === null && corruptedCount() === 0){ recover(new Date()); return; }
        accumulate();
        emitAll();
      }
    }
  
    function emitAll(){
      try{ renderActive(); renderHistory(); }catch(e){}
      window.MADCAT.emit("incidents");
    }
  
    // ---- rendering ------------------------------------------------------------
    function statusMeta(st){
      return st === "open"      ? { label: "Open",      ink: "var(--bad)",  tint: "var(--bad-dim)" }
           : st === "contained" ? { label: "Contained", ink: "var(--warn)", tint: "var(--warn-dim)" }
           :                       { label: "Recovered", ink: "var(--ok)",   tint: "var(--ok-dim)" };
    }
  
    function statBox(label, value, ink, sinceIso){
      const inner = sinceIso ? '<span data-since="' + sinceIso + '" data-mode="dur"></span>' : value;
      return '<div class="rounded-lg p-3" style="background:var(--panel-2)">' +
               '<div class="text-[11px]" style="color:var(--muted)">' + label + '</div>' +
               '<div class="mono mt-1" style="font-size:18px;color:' + (ink || 'var(--ink)') + '">' + inner + '</div>' +
             '</div>';
    }
  
    function renderActive(){
      const el = $("inc-active"); if(!el) return;
      const inc = registry.current;
      if(!inc){
        el.innerHTML =
          '<div class="card estate">' +
            '<div class="estate-icon" style="background:var(--ok-dim);color:var(--ok)">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5.5l-8-3-8 3V12c0 6 8 10 8 10Z"/><path d="m8.5 11.5 2.5 2.5 4.5-4.5"/></svg>' +
            '</div>' +
            '<h3 class="estate-title">No active incident</h3>' +
            '<p class="estate-text">The console opens a case automatically when bulk integrity corruption is detected on the data plane. Recovered cases appear in the history below.</p>' +
          '</div>';
        return;
      }
      const sm = statusMeta(inc.status);
      const tl = inc.timeline.slice().reverse().map(function(e){
        const dot = e.kind === "analyst" ? "var(--brand)" : e.kind === "auto" ? "var(--warn)" : "var(--muted)";
        return '<div class="tl-item"><span class="tl-dot" style="background:' + dot + '"></span>' +
                 '<div><div class="tl-text">' + e.text + '</div>' +
                 '<div class="tl-time mono">' + fmtTime(e.ts) + '</div></div></div>';
      }).join("");
      el.innerHTML =
        '<div class="card rounded-xl p-5" style="border-left:3px solid ' + sm.ink + '">' +
          '<div class="flex items-start justify-between gap-3">' +
            '<div>' +
              '<div class="flex items-center gap-2">' +
                '<span class="mono font-semibold" style="font-size:16px">' + inc.id + '</span>' +
                '<span class="inc-badge" style="color:' + sm.ink + ';background:' + sm.tint + '">' + sm.label + '</span>' +
              '</div>' +
              '<p class="text-[12.5px] mt-1" style="color:var(--muted)">' + inc.alertReason + '</p>' +
            '</div>' +
            '<div class="text-right text-[11px]" style="color:var(--muted)">opened <span data-since="' + inc.openedAt + '" data-mode="ago"></span></div>' +
          '</div>' +
          '<div class="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">' +
            statBox("Status", sm.label, sm.ink) +
            statBox("Systems affected", inc.peakSystems + " / 6", inc.peakSystems ? "var(--bad)" : "var(--ink)") +
            statBox("PHI records", inc.peakRecords, inc.peakRecords ? "var(--bad)" : "var(--ink)") +
            statBox("Elapsed", "", "var(--ink)", inc.openedAt) +
          '</div>' +
          '<div class="mt-4 flex flex-wrap gap-2 items-center">' +
            ((window.MADCAT.session && window.MADCAT.session.isReadOnly && window.MADCAT.session.isReadOnly())
              ? '<span class="text-[12px]" style="color:var(--muted)">Response actions require an operational role - read-only access (§164.312(a) Access Control).</span>'
              : ('<button class="btn" data-inc-action="ack">Acknowledge</button>' +
                 (inc.status === "open" ? '<button class="btn" data-inc-action="contain">Mark contained</button>' : '') +
                 '<button class="btn" data-inc-action="restore">Log: restore initiated</button>' +
                 '<button class="btn" data-inc-action="notify">Notify privacy officer</button>')) +
            '<button class="btn btn-brand" data-inc-open="' + inc.id + '">Open report</button>' +
          '</div>' +
          '<div class="mt-4"><div class="section-title">Timeline</div><div class="timeline">' + tl + '</div></div>' +
        '</div>';
      refreshTimes();
    }
  
    function renderHistory(){
      const t = $("inc-history"); if(!t) return;
      if(!registry.ledger.length){
        t.innerHTML = '<tbody><tr><td style="color:var(--muted);padding:1.25rem;text-align:center">No past incidents recorded.</td></tr></tbody>';
        return;
      }
      const head = '<thead><tr><th>Incident</th><th>Status</th><th>Opened</th><th>Duration</th><th>Peak systems</th><th>PHI records</th><th></th></tr></thead>';
      const rows = registry.ledger.map(function(inc){
        const sm = statusMeta(inc.status);
        const end = inc.recoveredAt || inc.containedAt || inc.openedAt;
        return '<tr>' +
          '<td class="mono">' + inc.id + '</td>' +
          '<td style="color:' + sm.ink + ';font-weight:600">' + sm.label + '</td>' +
          '<td class="mono">' + fmtTime(inc.openedAt) + '</td>' +
          '<td class="mono">' + durText(inc.openedAt, end) + '</td>' +
          '<td class="mono">' + inc.peakSystems + ' / 6</td>' +
          '<td class="mono">' + inc.peakRecords + '</td>' +
          '<td><button class="btn" data-inc-open="' + inc.id + '">Report</button></td>' +
        '</tr>';
      }).join("");
      t.innerHTML = head + '<tbody>' + rows + '</tbody>';
    }
  
    function refreshTimes(){
      const nodes = document.querySelectorAll('#inc-active [data-since]');
      nodes.forEach(function(el){
        const ms = new Date(el.getAttribute("data-since")).getTime();
        el.textContent = el.getAttribute("data-mode") === "ago"
          ? relAgo(ms)
          : durFromSecs(Math.max(0, Math.floor((Date.now() - ms)/1000)));
      });
    }
  
    function isVisible(){ const s = document.querySelector('[data-route="incidents"]'); return s && !s.hidden; }
  
    // ---- wiring ---------------------------------------------------------------
    document.addEventListener("click", function(ev){
      const a = ev.target.closest("[data-inc-action]");
      if(a){ action(a.getAttribute("data-inc-action")); return; }
      const o = ev.target.closest("[data-inc-open]");
      if(o){ registry.select(o.getAttribute("data-inc-open")); location.hash = "#/reports"; }
    });
  
    window.MADCAT.on("session", function(){ try{ renderActive(); }catch(e){} });
  
    if(typeof window.renderSummary === "function"){
      const prev = window.renderSummary;
      window.renderSummary = function(){
        prev.apply(this, arguments);
        try{ tick(); }catch(e){ }
      };
    }
  
    setInterval(function(){
      if(registry.current && registry.current.status === "open" && discoveryTs &&
         (Date.now() - lastActivity) >= QUIET_MS){
        contain(true);
      }
      if(isVisible()) refreshTimes();
    }, 1000);
  
    renderActive();
    renderHistory();
  })();