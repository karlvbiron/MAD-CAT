/* ============================================================
   Session.
   A cosmetic SSO gate + top-bar role switcher. No real auth - 
   it just records which role you're acting as, remembered in
   localStorage until Sign out. Populates MADCAT.session so the
   audit log's actor reflects the signed-in user, logs Session
   audit entries, and gates incident actions for the read-only
   role (a small §164.312(a) Access Control demonstration).
   Loads last; the bus (hipaa.js) and audit sink already exist.
   ============================================================ */
   (function(){
    const $ = id => document.getElementById(id);
    const KEY = "madcat.session";
  
    const IDENTITIES = [
      { id:"analyst",    name:"Dana Whitfield", role:"Security Analyst",   initials:"DW", readonly:false },
      { id:"privacy",    name:"Marcus Reed",    role:"Privacy Officer",    initials:"MR", readonly:false },
      { id:"compliance", name:"Elena Vasquez",  role:"Compliance Manager", initials:"EV", readonly:false },
      { id:"auditor",    name:"Sam Okafor",     role:"Read-only Auditor",  initials:"SO", readonly:true  },
    ];
    function byId(id){ return IDENTITIES.filter(function(x){ return x.id === id; })[0] || null; }
  
    function loadSaved(){
      try{ const s = JSON.parse(localStorage.getItem(KEY) || "null"); return s && s.id ? byId(s.id) : null; }
      catch(e){ return null; }
    }
    function persist(){ try{ localStorage.setItem(KEY, JSON.stringify(current ? { id: current.id } : null)); }catch(e){} }
  
    let current = null;
  
    const session = window.MADCAT.session = {
      actorLabel: function(){ return current ? (current.name + " · " + current.role) : "Unknown user"; },
      role: function(){ return current ? current.role : null; },
      isReadOnly: function(){ return !!(current && current.readonly); },
      identity: function(){ return current; },
      signIn: function(id){ apply(byId(id), "signin"); },
      switchTo: function(id){ if(current && current.id === id){ closeMenu(); return; } apply(byId(id), "switch"); },
      signOut: function(){ doSignOut(); },
    };
  
    function audit(cat, action, opts){ if(window.MADCAT.audit) window.MADCAT.audit.log(cat, action, opts); }
    function toast(t, o){ if(window.MADCAT.toast) window.MADCAT.toast(t, o); }
  
    function apply(idty, mode){
      if(!idty) return;
      current = idty;
      persist();
      updateChip();
      hideGate();
      closeMenu();
      window.MADCAT.emit("session");
      if(mode === "signin"){
        audit("session", "Signed in", { actor: session.actorLabel(), detail: "Role: " + current.role });
        toast("Signed in", { type: "success", msg: current.name + " · " + current.role });
      } else if(mode === "switch"){
        audit("session", "Switched to " + current.role, { actor: session.actorLabel() });
        toast("Role switched", { type: "info", msg: current.name + " · " + current.role });
      }
    }
  
    function doSignOut(){
      if(current) audit("session", "Signed out", { actor: session.actorLabel() });
      current = null;
      persist();
      closeMenu();
      updateChip();
      showGate();
      window.MADCAT.emit("session");
    }
  
    // ---- chrome ----
    function updateChip(){
      const c = current || IDENTITIES[0];
      if($("user-initials")) $("user-initials").textContent = c.initials;
      if($("user-name"))     $("user-name").textContent = c.name;
      if($("user-role"))     $("user-role").textContent = c.role;
    }
  
    function buildGate(){
      const el = $("sso-ids"); if(!el) return;
      el.innerHTML = IDENTITIES.map(function(i){
        return '<button class="sso-id" data-sso-id="' + i.id + '">' +
          '<span class="avatar">' + i.initials + '</span>' +
          '<span class="leading-tight">' +
            '<span class="user-item-name block">' + i.name + '</span>' +
            '<span class="user-item-role block">' + i.role + '</span>' +
          '</span></button>';
      }).join("");
    }
    function showGate(){ const g = $("sso-gate"); if(g) g.style.display = "flex"; }
    function hideGate(){ const g = $("sso-gate"); if(g) g.style.display = "none"; }
  
    function buildMenu(){
      const m = $("user-menu"); if(!m) return;
      m.innerHTML =
        '<div class="user-menu-h">Switch role</div>' +
        IDENTITIES.map(function(i){
          const on = current && current.id === i.id ? " user-item-on" : "";
          return '<button class="user-item' + on + '" data-switch-id="' + i.id + '">' +
            '<span class="avatar">' + i.initials + '</span>' +
            '<span class="leading-tight">' +
              '<span class="user-item-name block">' + i.name + '</span>' +
              '<span class="user-item-role block">' + i.role + '</span>' +
            '</span></button>';
        }).join("") +
        '<div class="user-menu-sep"></div>' +
        '<button class="user-signout" data-signout>Sign out</button>';
    }
    function openMenu(){ buildMenu(); const m = $("user-menu"); if(m) m.hidden = false; const c = $("user-chip"); if(c) c.setAttribute("aria-expanded", "true"); }
    function closeMenu(){ const m = $("user-menu"); if(m) m.hidden = true; const c = $("user-chip"); if(c) c.setAttribute("aria-expanded", "false"); }
    function toggleMenu(){ const m = $("user-menu"); if(m && m.hidden) openMenu(); else closeMenu(); }
  
    // ---- wiring ----
    document.addEventListener("click", function(ev){
      const sso = ev.target.closest ? ev.target.closest("[data-sso-id]") : null;
      if(sso){ session.signIn(sso.getAttribute("data-sso-id")); return; }
      const chip = ev.target.closest ? ev.target.closest("#user-chip") : null;
      if(chip){ toggleMenu(); return; }
      const sw = ev.target.closest ? ev.target.closest("[data-switch-id]") : null;
      if(sw){ session.switchTo(sw.getAttribute("data-switch-id")); return; }
      const so = ev.target.closest ? ev.target.closest("[data-signout]") : null;
      if(so){ doSignOut(); return; }
      if(!(ev.target.closest && ev.target.closest("#user-menu"))) closeMenu();
    });
  
    // ---- init ----
    buildGate();
    current = loadSaved();
    if(current){ updateChip(); hideGate(); }
    else { showGate(); }
    window.MADCAT.emit("session");
  })();