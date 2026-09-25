/* ============================================================
   Reports.
   Renders a print-to-PDF breach + incident report from a recorded
   incident's stored snapshot (so it's faithful to that incident's
   peak posture regardless of current wall state). Includes the
   four-factor Breach Risk Assessment (§164.402) and the NIST
   SP 800-66 crosswalk. No backend, no PDF dependency: window.print()
   + @media print CSS in app.css.
   ============================================================ */
   (function(){
    const $ = id => document.getElementById(id);
    const R = window.MADCAT.incidents;
    const U = window.MADCAT.util || {};
  
    function esc(s){ return String(s == null ? "" : s).replace(/[&<>]/g, function(ch){ return { "&":"&amp;", "<":"&lt;", ">":"&gt;" }[ch]; }); }
    function statusLabel(st){ return st === "open" ? "Open" : st === "contained" ? "Contained" : "Recovered"; }
    function statusInk(st){ return st === "open" ? "var(--bad)" : st === "contained" ? "var(--warn)" : "var(--ok)"; }
    function isVisible(){ const s = document.querySelector('[data-route="reports"]'); return s && !s.hidden; }
  
    function populateSelect(){
      const sel = $("rep-select"); if(!sel) return;
      const list = R ? R.all() : [];
      const cur = R ? R.subject() : null;
      sel.innerHTML = list.length
        ? list.map(function(inc){
            const active = (R.current && inc.id === R.current.id) ? " (active)" : "";
            const on = cur && inc.id === cur.id ? " selected" : "";
            return '<option value="' + inc.id + '"' + on + '>' + inc.id + active + '</option>';
          }).join("")
        : '<option value="">No incidents yet</option>';
    }
  
    function levelInk(impact){ return impact === "violated" ? "var(--bad)" : impact === "implicated" ? "var(--warn)" : "var(--ok)"; }
    function levelLabel(impact){ return impact === "violated" ? "Violated" : impact === "implicated" ? "Implicated" : "Compliant"; }
  
    function affectedSystemsTable(inc){
      const keys = Object.keys(inc.affected || {});
      if(!keys.length) return '<p class="rep-factor-d">No systems recorded as corrupted for this incident.</p>';
      const rows = keys.map(function(s){
        const v = (typeof SERVICES !== "undefined" && SERVICES[s]) ? SERVICES[s] : { name: s, role: "", ip: "" };
        return '<tr><td>' + esc(v.name) + '</td><td>' + esc(v.role) + '</td><td class="mono">' + esc(v.ip) + '</td>' +
               '<td class="mono">' + inc.affected[s] + '</td><td class="mono">§164.312(c)(1) Integrity</td></tr>';
      }).join("");
      return '<table class="report-table"><thead><tr><th>System</th><th>Role</th><th>Address</th>' +
             '<th>Records corrupted</th><th>Primary safeguard</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }
  
    function impactedSafeguards(comp){
      const out = [];
      (comp.families || []).forEach(function(fam){
        fam.cells.forEach(function(cl){
          if(cl.impact !== "ok"){
            out.push('<div class="rep-li"><span class="rep-dotb" style="background:' + levelInk(cl.impact) + '"></span>' +
                     '<div><span class="mono">' + esc(cl.id) + '</span> ' + esc(cl.name) +
                     ' - <span style="color:' + levelInk(cl.impact) + ';font-weight:600">' + levelLabel(cl.impact) + '</span>' +
                     (cl.ded ? ' (\u2212' + cl.ded + ')' : '') + '</div></div>');
          }
        });
      });
      return out.length ? out.join("") : '<p class="rep-factor-d">No safeguards impacted.</p>';
    }
  
    function crosswalkTable(comp){
      const rows = (comp.crosswalk || []).map(function(r){
        return '<tr><td class="mono">' + esc(r.id) + '</td><td>' + esc(r.name) + '</td>' +
               '<td class="mono">' + esc(r.csf) + '</td><td class="mono">' + esc(r.sp) + '</td>' +
               '<td style="color:' + levelInk(r.impact) + ';font-weight:600">' + levelLabel(r.impact) + '</td></tr>';
      }).join("");
      return '<table class="report-table"><thead><tr><th>HIPAA §</th><th>Safeguard</th>' +
             '<th>NIST CSF 2.0</th><th>SP 800-53 Rev. 5</th><th>Status</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }
  
    function fourFactors(inc, breach){
      const patients = breach ? breach.individuals : (inc.peakRecords || 0);
      const recovered = inc.status === "recovered";
      const factors = [
        { n: 1, t: "Nature and extent of the PHI involved",
          d: "Affected records carry up to 18 HIPAA identifiers each (names, dates, contact details, medical-record and account numbers) across approximately " + patients +
             " patients, spanning demographics, clinical notes, vital-sign streams, appointment and refill records, and billing data.",
          v: "Sensitive PHI; high identifiability." },
        { n: 2, t: "The unauthorized person who used the PHI or to whom the disclosure was made",
          d: "Activity is consistent with an automated external actor performing high-volume overwrites. No recipient of the data is identified; the event is an integrity/availability attack rather than a disclosure to a third party.",
          v: "No recipient identified; not a disclosure." },
        { n: 3, t: "Whether the PHI was actually acquired or viewed",
          d: "A Meow-style attack overwrites field values with non-conforming tokens; it destroys rather than reads data. There is no evidence PHI was exfiltrated, acquired, or viewed. This factor weighs against a confidentiality breach, though it does not resolve the integrity and availability compromise.",
          v: "Acquisition or viewing unlikely." },
        { n: 4, t: "The extent to which the risk to the PHI has been mitigated",
          d: recovered
            ? "Affected data was restored from verified, deterministic backups (restore_data.py), re-establishing integrity across all impacted systems. Residual risk is low following recovery."
            : "Mitigation is in progress. Restoration from verified backups is required to re-establish integrity across the impacted systems.",
          v: recovered ? "Risk mitigated via restore." : "Mitigation pending." },
      ];
      return factors.map(function(f){
        return '<div class="rep-factor"><div class="rep-factor-t">Factor ' + f.n + ": " + esc(f.t) + '</div>' +
               '<div class="rep-factor-d">' + esc(f.d) + '</div>' +
               '<div class="rep-factor-v">Determination: ' + esc(f.v) + '</div></div>';
      }).join("");
    }
  
    function notifications(breach){
      if(!breach){ return '<p class="rep-factor-d">No reportable breach recorded for this incident.</p>'; }
      const over = breach.over;
      const deadline = new Date(breach.deadline).toLocaleDateString();
      const items = [
        { ink: "var(--bad)",  t: "Notify affected individuals",
          d: "Written notice without unreasonable delay, no later than 60 days from discovery (by " + deadline + ")." },
        { ink: over ? "var(--bad)" : "var(--warn)", t: "Notify the HHS Secretary",
          d: over ? "\u2265 500 individuals: notify without unreasonable delay, within 60 days." : "< 500 individuals: record in the annual log filed with HHS." },
        { ink: over ? "var(--bad)" : "var(--muted)", t: "Notify prominent media",
          d: over ? "Required: \u2265 500 individuals in a state or jurisdiction." : "Not triggered below 500 individuals." },
      ];
      return items.map(function(i){
        return '<div class="rep-li"><span class="rep-dotb" style="background:' + i.ink + '"></span>' +
               '<div><span style="font-weight:600">' + esc(i.t) + '.</span> ' + esc(i.d) + '</div></div>';
      }).join("");
    }
  
    function buildReport(inc){
      const comp = inc.compliance || window.MADCAT.compliance || { families: [], crosswalk: [], cia: {}, score: 100, status: "Compliant" };
      const breach = comp.breach || null;
      const genAt = new Date().toLocaleString();
      const end = inc.recoveredAt || inc.containedAt || inc.openedAt;
      const dur = U.durText ? U.durText(inc.openedAt, end) : "";
      const cia = comp.cia || {};
      const ciaText = "Confidentiality " + (cia.C ? "impacted" : "not read") +
                      ", Integrity " + (cia.I ? "impacted" : "intact") +
                      ", Availability " + (cia.A ? "impacted" : "intact") + ".";
  
      return '' +
      '<article class="report-doc">' +
        '<div class="rep-masthead">' +
          '<div><div class="rep-org">St. Regis Health System</div>' +
               '<div class="rep-org-sub">Security &amp; Compliance Console</div></div>' +
          '<div class="rep-confidential">CONFIDENTIAL · CONTAINS PHI</div>' +
        '</div>' +
  
        '<div class="rep-title">Security Incident &amp; Breach Assessment Report</div>' +
        '<div class="rep-meta">Incident ' + esc(inc.id) + ' · Status ' +
          '<span style="color:' + statusInk(inc.status) + ';font-weight:600">' + statusLabel(inc.status) + '</span>' +
          ' · Generated ' + esc(genAt) + '</div>' +
  
        '<div class="rep-h2">1. Incident summary</div>' +
        '<dl class="rep-dl">' +
          '<dt>Incident ID</dt><dd class="mono">' + esc(inc.id) + '</dd>' +
          '<dt>Status</dt><dd>' + statusLabel(inc.status) + '</dd>' +
          '<dt>Discovered</dt><dd class="mono">' + esc(U.fmtTime ? U.fmtTime(inc.openedAt) : inc.openedAt) + '</dd>' +
          '<dt>Contained</dt><dd class="mono">' + (inc.containedAt ? esc(U.fmtTime(inc.containedAt)) : " - ") + '</dd>' +
          '<dt>Recovered</dt><dd class="mono">' + (inc.recoveredAt ? esc(U.fmtTime(inc.recoveredAt)) : " - ") + '</dd>' +
          '<dt>Duration</dt><dd class="mono">' + esc(dur) + '</dd>' +
          '<dt>Detection</dt><dd>' + esc(inc.alertReason) + '</dd>' +
          '<dt>Systems affected</dt><dd class="mono">' + inc.peakSystems + ' / 6</dd>' +
          '<dt>PHI records affected</dt><dd class="mono">' + inc.peakRecords + '</dd>' +
        '</dl>' +
  
        '<div class="rep-h2">2. Affected systems</div>' +
        affectedSystemsTable(inc) +
  
        '<div class="rep-h2">3. HIPAA Security Rule impact</div>' +
        '<dl class="rep-dl">' +
          '<dt>Compliance posture</dt><dd><span class="mono">' + comp.score + ' / 100</span> · ' + esc(comp.status) + '</dd>' +
          '<dt>CIA triad</dt><dd>' + esc(ciaText) + '</dd>' +
        '</dl>' +
        '<div style="margin-top:.5rem">' + impactedSafeguards(comp) + '</div>' +
  
        '<div class="rep-h2">4. Four-factor Breach Risk Assessment (§164.402)</div>' +
        fourFactors(inc, breach) +
        '<div class="rep-note">Because a Meow attack compromises integrity and availability rather than confidentiality, ' +
          'the four-factor assessment weighs toward a low probability that PHI was acquired or viewed. However, the impermissible ' +
          'alteration and loss of availability of PHI is itself a compromise of the Security Rule\'s integrity and availability ' +
          'requirements, and is handled as a reportable integrity/availability incident.</div>' +
  
        '<div class="rep-h2">5. Notification obligations (§164.404 / §164.406 / §164.408)</div>' +
        notifications(breach) +
  
        '<div class="rep-h2">6. Control crosswalk (NIST SP 800-66 Rev. 2)</div>' +
        crosswalkTable(comp) +
  
        '<div class="rep-h2">7. Incident timeline</div>' +
        '<div>' + (inc.timeline || []).map(function(e){
          return '<div class="rep-li"><span class="rep-dotb" style="background:var(--muted)"></span>' +
                 '<div><span class="mono" style="color:var(--muted)">' + esc(U.fmtTime ? U.fmtTime(e.ts) : e.ts) + '</span> - ' + esc(e.text) + '</div></div>';
        }).join("") + '</div>' +
  
        '<div class="rep-foot">Generated by the St. Regis Health System Security &amp; Compliance Console, generated ' + esc(genAt) +
          '. Internal working document; not legal advice.</div>' +
      '</article>';
    }
  
    function renderReports(){
      populateSelect();
      const doc = $("report-doc"); if(!doc) return;
      const inc = R ? R.subject() : null;
      if(!inc){
        doc.innerHTML =
          '<div class="card estate">' +
            '<div class="estate-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2.5H7A2 2 0 0 0 5 4.5v15a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7.5Z"/><path d="M14 2.5v5h5"/><line x1="8.5" y1="13" x2="15.5" y2="13"/><line x1="8.5" y1="16.5" x2="13.5" y2="16.5"/></svg></div>' +
            '<h3 class="estate-title">No incident to report</h3>' +
            '<p class="estate-text">A report is generated from a recorded incident. Run an attack to open one, then return here to print or save it as a PDF.</p>' +
          '</div>';
        return;
      }
      doc.innerHTML = buildReport(inc);
    }
  
    // ---- wiring ---------------------------------------------------------------
    const sel = $("rep-select");
    if(sel) sel.addEventListener("change", function(){ if(R) R.select(this.value); });
    const btn = $("rep-print");
    if(btn) btn.addEventListener("click", function(){
      const inc = R ? R.subject() : null;
      if(window.MADCAT.audit && inc) window.MADCAT.audit.log("report", "Generated report for " + inc.id, { ref: inc.id });
      if(window.MADCAT.toast && inc) window.MADCAT.toast("Report generated", { type: "info", msg: "Incident " + inc.id });
      window.print();
    });
  
    window.MADCAT.on("incidents", function(){ renderReports(); });
    window.addEventListener("hashchange", function(){ if(isVisible()) renderReports(); });
  
    renderReports();
  })();