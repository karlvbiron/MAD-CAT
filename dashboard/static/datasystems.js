/* ============================================================
   Data Systems.
   Asset inventory + per-system detail + a live system-level
   topology of the shared 25-patient roster. Everything derives
   from the wall's live global state[]; no backend, no new data.
   Chains onto renderSummary (try/catch-guarded) so the inventory
   and topology tint live as systems fall and recover.
   ============================================================ */
   (function(){
    const $ = id => document.getElementById(id);
  
    // Static asset register (merged with the wall's SERVICES for name/ip/role).
    const ASSETS = {
      mongodb:       { kind:"Document store",         store:"my_database / my_table", records:"25 documents", owner:"Clinical Applications",        sor:true },
      elasticsearch: { kind:"Search index",           store:"my_index",               records:"25 documents", owner:"Clinical Informatics" },
      cassandra:     { kind:"Wide-column store",       store:"my_keyspace / my_table",  records:"25 rows",      owner:"Biomedical Engineering" },
      redis:         { kind:"Key-value store",         store:"db 0 · user:*",           records:"25 keys",      owner:"Platform Engineering" },
      couchdb:       { kind:"Document store",          store:"my_database",             records:"25 documents", owner:"Clinical Applications" },
      hadoop:        { kind:"Distributed file system", store:"/user/data",              records:"25 files",     owner:"Revenue Cycle / Data Platform" },
    };
  
    // Topology node positions (SVG viewBox 720x400), MongoDB at top.
    const POS = {
      mongodb:      { x:360, y:40  },
      elasticsearch:{ x:499, y:120 },
      cassandra:    { x:499, y:280 },
      redis:        { x:360, y:360 },
      couchdb:      { x:221, y:280 },
      hadoop:       { x:221, y:120 },
    };
    const HUB = { x:360, y:200 };
  
    let selected = "mongodb";
  
    function liveStatus(s){
      const st = state[s].state;
      return st === "corrupted" ? { label:"Corrupted",   ink:"var(--bad)",  tint:"var(--bad-dim)" }
           : st === "active"    ? { label:"Active",       ink:"var(--warn)", tint:"var(--warn-dim)" }
           :                      { label:"Operational",  ink:"var(--ok)",   tint:"var(--ok-dim)" };
    }
  
    // ---- inventory table ------------------------------------------------------
    function renderInventory(){
      const t = $("ds-table"); if(!t) return;
      const head = '<thead><tr><th>System</th><th>Address</th><th>Clinical role</th><th>Records</th><th>Status</th></tr></thead>';
      const rows = ORDER.map(function(s){
        const v = SERVICES[s], a = ASSETS[s], ls = liveStatus(s);
        const cls = s === selected ? ' class="ds-row-active"' : '';
        return '<tr data-ds-row="' + s + '"' + cls + ' style="cursor:pointer">' +
          '<td><div style="font-weight:600">' + v.name + '</div>' +
              '<div class="text-[11px]" style="color:var(--muted)">' + a.kind + '</div></td>' +
          '<td class="mono">' + v.ip + '</td>' +
          '<td>' + v.role + '</td>' +
          '<td class="mono">' + a.records + '</td>' +
          '<td><span class="inc-badge" style="color:' + ls.ink + ';background:' + ls.tint + '">' + ls.label + '</span></td>' +
        '</tr>';
      }).join("");
      t.innerHTML = head + '<tbody>' + rows + '</tbody>';
    }
  
    // ---- detail card ----------------------------------------------------------
    function fact(label, value, mono){
      return '<div class="rounded-lg p-3" style="background:var(--panel-2)">' +
               '<div class="text-[11px]" style="color:var(--muted)">' + label + '</div>' +
               '<div class="' + (mono ? "mono " : "") + 'text-[12.5px] mt-1">' + value + '</div>' +
             '</div>';
    }
  
    function renderDetail(){
      const el = $("ds-detail"); if(!el) return;
      const s = selected, v = SERVICES[s], a = ASSETS[s], ls = liveStatus(s);
      const corrupted = state[s].state === "corrupted";
      el.innerHTML =
        '<div class="card rounded-xl p-5" style="border-left:3px solid ' + ls.ink + '">' +
          '<div class="flex items-start justify-between gap-3">' +
            '<div>' +
              '<div class="flex items-center gap-2 flex-wrap">' +
                '<span class="font-semibold" style="font-size:16px">' + v.name + '</span>' +
                (a.sor ? '<span class="tag-brand">System of record</span>' : '') +
                '<span class="inc-badge" style="color:' + ls.ink + ';background:' + ls.tint + '">' + ls.label + '</span>' +
              '</div>' +
              '<p class="text-[12.5px] mt-1" style="color:var(--muted)">' + a.kind + ' · ' + v.role + '</p>' +
            '</div>' +
            '<div class="text-right text-[11px]" style="color:var(--muted)">' + (state[s].at ? ("last change " + state[s].at) : "no changes") + '</div>' +
          '</div>' +
          '<div class="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">' +
            fact("Address", v.ip, true) +
            fact("Data store", a.store, true) +
            fact("Records", a.records) +
            fact("Classification", "PHI") +
            fact("Owner", a.owner) +
            fact("Primary safeguard", "§164.312(c)(1) Integrity", true) +
          '</div>' +
          (corrupted
            ? '<div class="mt-3 text-[12px]" style="color:var(--bad)">' + state[s].records + ' record' + (state[s].records === 1 ? "" : "s") + ' currently corrupted - integrity violated.</div>'
            : '') +
          '<p class="text-[11px] mt-3" style="color:var(--muted)">Carries up to 18 HIPAA identifiers per record; linked to the shared 25-patient roster by patient_id / email.</p>' +
        '</div>';
    }
  
    // ---- topology / lineage ---------------------------------------------------
    function renderTopo(){
      const el = $("ds-topo"); if(!el) return;
      const cCount = ORDER.filter(function(s){ return state[s].state === "corrupted"; }).length;
      const anyC = cCount > 0;
  
      const edges = ORDER.map(function(s){
        const p = POS[s], st = state[s].state;
        const col = st === "corrupted" ? "var(--bad)" : st === "active" ? "var(--warn)" : "var(--line)";
        const w = st === "operational" ? 1.5 : 2.5;
        const dash = st === "corrupted" ? ' stroke-dasharray="5 4"' : "";
        return '<line x1="' + HUB.x + '" y1="' + HUB.y + '" x2="' + p.x + '" y2="' + p.y +
               '" style="stroke:' + col + '" stroke-width="' + w + '"' + dash + "/>";
      }).join("");
  
      const hubStroke = anyC ? "var(--bad)" : "var(--ok)";
      const hubLine3  = anyC ? (cCount + "/6 systems compromised") : "integrity intact";
      const hubLine3c = anyC ? "var(--bad)" : "var(--ok)";
      const hub =
        '<rect x="' + (HUB.x-78) + '" y="' + (HUB.y-33) + '" width="156" height="66" rx="12" style="fill:var(--panel);stroke:' + hubStroke + '" stroke-width="2"/>' +
        '<text x="' + HUB.x + '" y="' + (HUB.y-13) + '" text-anchor="middle" style="fill:var(--ink);font-weight:600" font-size="12">Patient roster</text>' +
        '<text x="' + HUB.x + '" y="' + (HUB.y+3)  + '" text-anchor="middle" style="fill:var(--muted)" font-size="10">25 shared identities</text>' +
        '<text x="' + HUB.x + '" y="' + (HUB.y+20) + '" text-anchor="middle" class="mono" style="fill:' + hubLine3c + ';font-weight:600" font-size="10">' + hubLine3 + '</text>';
  
      const nodes = ORDER.map(function(s){
        const p = POS[s], v = SERVICES[s], ls = liveStatus(s);
        const short = v.name.replace(" HDFS", "");
        const sor = ASSETS[s].sor
          ? '<text x="' + p.x + '" y="' + (p.y-32) + '" text-anchor="middle" style="fill:var(--muted)" font-size="8.5">system of record</text>'
          : "";
        return '<g data-ds-node="' + s + '" style="cursor:pointer">' +
          '<rect x="' + (p.x-66) + '" y="' + (p.y-23) + '" width="132" height="46" rx="10" style="fill:' + ls.tint + ';stroke:' + ls.ink + '" stroke-width="' + (s === selected ? 2.5 : 1.5) + '"/>' +
          '<text x="' + p.x + '" y="' + (p.y-3) + '" text-anchor="middle" style="fill:var(--ink);font-weight:600" font-size="12">' + short + '</text>' +
          '<text x="' + p.x + '" y="' + (p.y+13) + '" text-anchor="middle" class="mono" style="fill:' + ls.ink + ';font-weight:600" font-size="9.5">' + ls.label + '</text>' +
          sor +
        '</g>';
      }).join("");
  
      el.innerHTML =
        '<svg viewBox="0 -22 720 422" style="width:100%;height:auto;max-width:760px;display:block;margin:0 auto" xmlns="http://www.w3.org/2000/svg">' +
          edges + hub + nodes +
        '</svg>';
    }
  
    function renderDS(){ renderInventory(); renderDetail(); renderTopo(); }
  
    // ---- wiring ---------------------------------------------------------------
    document.addEventListener("click", function(ev){
      const row  = ev.target.closest ? ev.target.closest("[data-ds-row]")  : null;
      const node = ev.target.closest ? ev.target.closest("[data-ds-node]") : null;
      const pick = row ? row.getAttribute("data-ds-row") : node ? node.getAttribute("data-ds-node") : null;
      if(pick && pick !== selected){ selected = pick; renderDS(); }
      else if(pick){ renderDS(); }
    });
  
    if(typeof window.renderSummary === "function"){
      const prev = window.renderSummary;
      window.renderSummary = function(){
        prev.apply(this, arguments);
        try{ renderDS(); }catch(e){ }
      };
    }
  
    renderDS();
  })();