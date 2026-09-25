/* ============================================================
   Audit Log.
   A console-wide, append-only, newest-first activity log,
   distinct from the per-incident timeline. Defines the shared
   MADCAT.audit sink (localStorage-backed, capped), which
   incidents.js and reports.js write to, and renders the Audit
   Log tab with category filters and relative timestamps.
   No backend; loads after hipaa.js (which sets up the bus).
   ============================================================ */
   (function(){
    const $ = id => document.getElementById(id);
    const CAP = 500;
    const KEY = "madcat.audit";
  
    function load(){ try{ return JSON.parse(localStorage.getItem(KEY) || "[]"); }catch(e){ return []; } }
    function save(list){ try{ localStorage.setItem(KEY, JSON.stringify(list)); }catch(e){} }
  
    // Actor defaults to the signed-in user once session.js provides one.
    function actorOf(opts){
      if(opts && opts.actor) return opts.actor;
      const s = window.MADCAT.session;
      return (s && s.actorLabel && s.actorLabel()) || "Dana Whitfield · Security Analyst";
    }
  
    const sink = window.MADCAT.audit = {
      entries: load(),
      log: function(category, action, opts){
        opts = opts || {};
        const e = {
          ts: new Date().toISOString(),
          category: category, action: action,
          actor: actorOf(opts), detail: opts.detail || "", ref: opts.ref || "",
        };
        this.entries.unshift(e);
        if(this.entries.length > CAP) this.entries.length = CAP;
        save(this.entries);
        window.MADCAT.emit("audit");
        return e;
      },
      clear: function(){ this.entries = []; save([]); window.MADCAT.emit("audit"); },
    };
  
    const CATS = [
      { key:"all",      label:"All" },
      { key:"incident", label:"Incident", ink:"var(--warn)" },
      { key:"response", label:"Response", ink:"var(--brand)" },
      { key:"report",   label:"Report",   ink:"var(--ink)" },
      { key:"system",   label:"System",   ink:"var(--muted)" },
      { key:"session",  label:"Session",  ink:"var(--ok)" },
    ];
    function cat(k){ return CATS.filter(function(c){ return c.key === k; })[0]; }
    function catInk(k){ const c = cat(k); return (c && c.ink) || "var(--muted)"; }
    function catLabel(k){ const c = cat(k); return c ? c.label : k; }
  
    let filter = "all";
  
    function two(n){ return String(n).padStart(2, "0"); }
    function rel(iso){
      const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime())/1000));
      if(s < 10) return "just now";
      if(s < 60) return s + "s ago";
      const m = Math.floor(s/60); if(m < 60) return m + "m ago";
      const h = Math.floor(m/60); if(h < 24) return h + "h " + two(m%60) + "m ago";
      return Math.floor(h/24) + "d ago";
    }
    function fmtAbs(iso){ try{ return new Date(iso).toLocaleString(); }catch(e){ return iso; } }
    function esc(s){ return String(s == null ? "" : s).replace(/[&<>]/g, function(ch){ return { "&":"&amp;","<":"&lt;",">":"&gt;" }[ch]; }); }
  
    function renderChips(){
      const el = $("audit-filters"); if(!el) return;
      el.innerHTML = CATS.map(function(c){
        const n = c.key === "all" ? sink.entries.length : sink.entries.filter(function(e){ return e.category === c.key; }).length;
        const on = c.key === filter;
        return '<button class="audit-chip' + (on ? " audit-chip-on" : "") + '" data-audit-filter="' + c.key + '">' +
               c.label + ' <span class="audit-chip-n">' + n + '</span></button>';
      }).join("");
    }
  
    function renderList(){
      const el = $("audit-list"); if(!el) return;
      const items = sink.entries.filter(function(e){ return filter === "all" || e.category === filter; });
      if(!items.length){
        el.innerHTML = '<div style="padding:1.5rem;text-align:center;color:var(--muted);font-size:12.5px">' +
          (sink.entries.length ? "No entries in this category."
                               : "No activity recorded yet. Console events appear here as incidents are raised and actions are taken.") +
          '</div>';
        return;
      }
      el.innerHTML = items.map(function(e){
        const ink = catInk(e.category);
        return '<div class="audit-row">' +
          '<span class="audit-dot" style="background:' + ink + '"></span>' +
          '<div class="min-w-0" style="flex:1">' +
            '<div class="audit-action">' + esc(e.action) +
              (e.ref ? ' <span class="mono" style="color:var(--muted)">· ' + esc(e.ref) + '</span>' : '') + '</div>' +
            (e.detail ? '<div class="audit-detail">' + esc(e.detail) + '</div>' : '') +
            '<div class="audit-meta">' + esc(e.actor) + ' · <span data-since="' + e.ts + '" title="' + esc(fmtAbs(e.ts)) + '">' + rel(e.ts) + '</span></div>' +
          '</div>' +
          '<span class="audit-cat" style="color:' + ink + '">' + catLabel(e.category) + '</span>' +
        '</div>';
      }).join("");
    }
  
    function render(){ renderChips(); renderList(); }
  
    function isVisible(){ const s = document.querySelector('[data-route="audit"]'); return s && !s.hidden; }
    function refreshTimes(){
      document.querySelectorAll('#audit-list [data-since]').forEach(function(el){
        el.textContent = rel(el.getAttribute("data-since"));
      });
    }
  
    // ---- wiring ----
    document.addEventListener("click", function(ev){
      const f = ev.target.closest ? ev.target.closest("[data-audit-filter]") : null;
      if(f){ filter = f.getAttribute("data-audit-filter"); render(); return; }
      const c = ev.target.closest ? ev.target.closest("[data-audit-clear]") : null;
      if(c){ if(window.confirm("Clear the audit log? This cannot be undone.")) sink.clear(); }
    });
    window.MADCAT.on("audit", render);
    window.addEventListener("hashchange", function(){ if(isVisible()) render(); });
    setInterval(function(){ if(isVisible()) refreshTimes(); }, 1000);
  
    render();
  })();