(function(){
    const ROUTES  = ["overview","data-systems","incidents","hipaa","reports","audit"];
    const secs    = document.querySelectorAll("[data-route]");
    const navs    = document.querySelectorAll("[data-nav]");
    const sidebar = document.getElementById("sidebar");
    const backdrop= document.getElementById("backdrop");
    const menuBtn = document.getElementById("menu-btn");
    const header  = document.getElementById("appheader");
  
    function openSidebar(){ sidebar.classList.add("open"); backdrop.classList.add("show"); }
    function closeSidebar(){ sidebar.classList.remove("open"); backdrop.classList.remove("show"); }
  
    function routeFromHash(){
      const r = (location.hash || "").replace(/^#\/?/, "");
      return ROUTES.includes(r) ? r : "overview";
    }
  
    function show(r){
      secs.forEach(sec => { sec.hidden = (sec.getAttribute("data-route") !== r); });
      navs.forEach(a => {
        const on = a.getAttribute("data-nav") === r;
        a.classList.toggle("nav-active", on);
        if(on) a.setAttribute("aria-current","page"); else a.removeAttribute("aria-current");
      });
      closeSidebar();
      window.scrollTo({top:0});
      // returning to Overview: keep the live feed pinned to the newest line
      if(r === "overview"){ const f = document.getElementById("feed"); if(f) f.scrollTop = f.scrollHeight; }
    }
  
    function syncHeader(){
      if(header) document.documentElement.style.setProperty("--header-h", header.offsetHeight + "px");
    }
  
    navs.forEach(a => a.addEventListener("click", e => {
      e.preventDefault();
      location.hash = "#/" + a.getAttribute("data-nav");
    }));
    window.addEventListener("hashchange", () => show(routeFromHash()));
    if(menuBtn)  menuBtn.addEventListener("click", openSidebar);
    if(backdrop) backdrop.addEventListener("click", closeSidebar);
    window.addEventListener("resize", syncHeader);
  
    syncHeader();
    show(routeFromHash());
  })();