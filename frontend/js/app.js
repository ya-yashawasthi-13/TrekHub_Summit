(function () {
    const API = `/api`;
    const $ = (sel, ctx = document) => ctx.querySelector(sel);
    const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

    const SESSION_ID = (() => {
        let s = localStorage.getItem("th_session");
        if (!s) { s = "sess_" + Math.random().toString(36).slice(2, 10); localStorage.setItem("th_session", s); }
        return s;
    })();

    async function api(path, opts = {}) {
        const res = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...opts });
        if (!res.ok) {
            let msg = res.statusText;
            try { msg = (await res.json()).error || msg; } catch (_) { }
            throw new Error(msg);
        }
        return res.json();
    }

    function escapeHtml(s) {
        return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    function trekCardHtml(t) {
        const diffColor = { Easy: "#2e5d4e", Moderate: "#c1502e", Difficult: "#7a1f1f" }[t.difficulty] || "#17262d";
        const score = t.match_score != null ? `<span class="tc-score">Match ${t.match_score}</span>` : "";
        return `
      <div class="col-md-6 col-lg-4">
        <div class="trek-card" data-trek-id="${t.id}">
          <div class="tc-img"><span class="tc-diff" style="background:${diffColor}">${escapeHtml(t.difficulty)}</span></div>
          <div class="tc-body">
            <h5>${escapeHtml(t.name)}</h5>
            <div class="text-muted small">${escapeHtml(t.state)}${t.region ? " · " + escapeHtml(t.region) : ""}</div>
            <p class="mt-2 mb-2 small">${escapeHtml((t.description || "").slice(0, 110))}${(t.description || "").length > 110 ? "…" : ""}</p>
            <div class="tc-meta">
              <span>${t.duration_days} days</span>
              <span>${t.cost_inr.toLocaleString("en-IN")}</span>
              ${t.distance_km ? `<span>${t.distance_km} km</span>` : ""}
              ${t.best_time ? `<span>${escapeHtml(t.best_time)}</span>` : ""}
              ${score}
            </div>
          </div>
        </div>
      </div>`;
    }

    function renderGrid(container, treks, emptyMsg) {
        if (!treks || treks.length === 0) { container.innerHTML = `<div class="col-12 text-center text-muted py-5">${emptyMsg}</div>`; return; }
        container.innerHTML = treks.map(trekCardHtml).join("");
        $$(".trek-card", container).forEach(el => el.addEventListener("click", () => openTrekModal(el.dataset.trekId)));
    }

    async function loadStates() {
        const states = await api("/states");
        for (const sel of [$("#stateSelect"), $("#recState")]) {
            if (!sel) continue;
            const cur = sel.value;
            sel.innerHTML = `<option value="">Any</option>` + states.map(s => `<option>${escapeHtml(s)}</option>`).join("");
            sel.value = cur;
        }
    }

    async function loadTreks(params = {}) {
        const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
        const data = await api("/treks" + (qs.toString() ? "?" + qs : ""));
        renderGrid($("#treksGrid"), data, "No treks match those filters.");
        if ($("#statTotal")) $("#statTotal").textContent = data.length;
        if ($("#statStates")) $("#statStates").textContent = new Set(data.map(t => t.state)).size;
    }

    $("#filterForm").addEventListener("submit", e => {
        e.preventDefault();
        loadTreks(Object.fromEntries(new FormData(e.target).entries())).catch(err => console.error(err.message));
    });

    $("#recommendForm").addEventListener("submit", async e => {
        e.preventDefault();
        const fd = Object.fromEntries(new FormData(e.target).entries());
        const body = {
            state: fd.state || null, difficulty: fd.difficulty || null,
            budget: fd.budget ? +fd.budget : null, days: fd.days ? +fd.days : null,
        };
        const target = $("#recommendResults");
        target.innerHTML = `<div class="text-muted">Scoring treks…</div>`;
        try {
            const data = await api("/recommend", { method: "POST", body: JSON.stringify(body) });
            if (!data.length) { target.innerHTML = `<div class="alert alert-warning">No treks scored above zero.</div>`; return; }
            target.innerHTML = `<div class="row g-3">${data.map(trekCardHtml).join("")}</div>`;
            $$(".trek-card", target).forEach(el => el.addEventListener("click", () => openTrekModal(el.dataset.trekId)));
        } catch (err) { target.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`; }
    });

    $("#nlpForm").addEventListener("submit", async e => {
        e.preventDefault();
        const query = $("#nlpQuery").value.trim();
        if (!query) return;
        const filtersEl = $("#nlpFilters"), resultsEl = $("#nlpResults");
        filtersEl.textContent = "Understanding your query…"; resultsEl.innerHTML = "";
        try {
            const data = await api("/search/nlp", { method: "POST", body: JSON.stringify({ query }) });
            const f = data.filters || {}; const pills = [];
            if (f.state) pills.push(`State: ${f.state}`);
            if (f.difficulty) pills.push(`Difficulty: ${f.difficulty}`);
            if (f.budget) pills.push(`Budget ≤ ₹${f.budget}`);
            if (f.days) pills.push(`Days ≤ ${f.days}`);
            filtersEl.innerHTML = (data.used_ai ? `<i class="bi bi-stars me-1"></i>Parsed by AI · ` : `<i class="bi bi-cpu me-1"></i>Parsed locally · `) +
                (pills.length ? pills.map(p => `<span class="badge bg-light text-dark me-1">${p}</span>`).join("") : "No filters detected");
            if (!(data.results || []).length) { resultsEl.innerHTML = `<div class="col-12"><div class="alert alert-light">No matches. Try different words.</div></div>`; return; }
            resultsEl.innerHTML = data.results.map(trekCardHtml).join("");
            $$(".trek-card", resultsEl).forEach(el => el.addEventListener("click", () => openTrekModal(el.dataset.trekId)));
        } catch (err) {
            filtersEl.textContent = "";
            resultsEl.innerHTML = `<div class="col-12"><div class="alert alert-danger">${escapeHtml(err.message)}</div></div>`;
        }
    });

    $("#addForm").addEventListener("submit", async e => {
        e.preventDefault();
        const fd = Object.fromEntries(new FormData(e.target).entries());
        const msg = $("#addMsg");
        msg.innerHTML = `<span class="text-muted">Saving…</span>`;
        try {
            const created = await api("/treks", { method: "POST", body: JSON.stringify(fd) });
            msg.innerHTML = `<span class="text-success"><i class="bi bi-check-circle me-1"></i>Added "${escapeHtml(created.name)}"</span>`;
            e.target.reset();
            await Promise.all([loadTreks(), loadStates()]);
        } catch (err) { msg.innerHTML = `<span class="text-danger">${escapeHtml(err.message)}</span>`; }
    });

    async function openTrekModal(id) {
        try {
            const t = await api(`/treks/${id}`);
            const diffColor = { Easy: "#2e5d4e", Moderate: "#c1502e", Difficult: "#7a1f1f" }[t.difficulty] || "#17262d";
            $("#trekModalContent").innerHTML = `
        <div class="tc-img position-relative">
          <span class="tc-diff" style="background:${diffColor};top:16px;right:16px">${escapeHtml(t.difficulty)}</span>
        </div>
        <div class="p-4">
          <h3 class="th-heading">${escapeHtml(t.name)}</h3>
          <div class="text-muted">${escapeHtml(t.state)}${t.region ? " · " + escapeHtml(t.region) : ""}</div>
          <div class="row g-3 my-3">
            <div class="col-6 col-md-3"><small class="text-muted d-block">Duration</small><strong>${t.duration_days} days</strong></div>
            <div class="col-6 col-md-3"><small class="text-muted d-block">Distance</small><strong>${t.distance_km ?? "—"} km</strong></div>
            <div class="col-6 col-md-3"><small class="text-muted d-block">Cost</small><strong>₹${t.cost_inr.toLocaleString("en-IN")}</strong></div>
            <div class="col-6 col-md-3"><small class="text-muted d-block">Max altitude</small><strong>${t.max_altitude_ft ? t.max_altitude_ft + " ft" : "—"}</strong></div>
            <div class="col-12"><small class="text-muted d-block">Best time to visit</small><strong>${escapeHtml(t.best_time || "—")}</strong></div>
          </div>
          <p>${escapeHtml(t.description || "")}</p>
          <div class="text-end"><button class="btn btn-dark" data-bs-dismiss="modal">Close</button></div>
        </div>`;
            new bootstrap.Modal($("#trekModal")).show();
        } catch (err) { console.error(err.message); }
    }

    const chatToggle = $("#chatToggle"), chatPanel = $("#chatPanel"), chatClose = $("#chatClose"),
        chatForm = $("#chatForm"), chatInput = $("#chatInput"), chatMessages = $("#chatMessages");

    function addMsg(role, text, { typing = false } = {}) {
        const el = document.createElement("div");
        el.className = "msg " + (role === "user" ? "user" : "bot") + (typing ? " typing" : "");
        el.textContent = text;
        chatMessages.appendChild(el);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return el;
    }

    if (chatToggle) {
        chatToggle.addEventListener("click", async () => {
            const show = chatPanel.hasAttribute("hidden");
            if (show) {
                chatPanel.removeAttribute("hidden");
                if (!chatMessages.hasChildNodes()) {
                    addMsg("bot", "Namaste! I'm your AI trek guide. Ask me about treks, seasons, fitness or gear.");
                    try {
                        const hist = await api(`/chat/history?session_id=${encodeURIComponent(SESSION_ID)}`);
                        for (const h of hist) addMsg(h.role, h.content);
                    } catch (_) { }
                }
                chatInput.focus();
            } else chatPanel.setAttribute("hidden", "");
        });
        chatClose.addEventListener("click", () => chatPanel.setAttribute("hidden", ""));

        chatForm.addEventListener("submit", async e => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;
            addMsg("user", text);
            chatInput.value = "";
            const typingEl = addMsg("bot", "Thinking…", { typing: true });
            try {
                const data = await api("/chat", { method: "POST", body: JSON.stringify({ message: text, session_id: SESSION_ID }) });
                typingEl.remove(); addMsg("bot", data.reply || "…");
            } catch (err) { typingEl.remove(); addMsg("bot", "Error: " + err.message); }
        });
    }

    async function loadFaqs() {
        const container = $("#faqAccordion");
        if (!container) return;
        
        try {
            const faqs = await api("/faq");
            if (!faqs || faqs.length === 0) {
                container.innerHTML = '<div class="text-center text-muted p-4">No questions yet. Be the first to ask!</div>';
                return;
            }
            
            const userStr = localStorage.getItem('user');
            const currentUser = userStr ? JSON.parse(userStr) : null;
            
            container.innerHTML = faqs.map((q, idx) => `
                <div class="accordion-item border-0 ${idx > 0 ? 'border-top' : ''}">
                    <h2 class="accordion-header position-relative">
                        <button class="accordion-button collapsed fw-semibold" type="button" data-bs-toggle="collapse" data-bs-target="#faqItem${q.id}">
                            <div class="d-flex flex-column text-start w-100 pe-4">
                                <div class="pe-3">${escapeHtml(q.question_text)}</div>
                                <div class="text-muted mt-1 fw-normal" style="font-size: 0.8rem;">
                                    by ${escapeHtml(q.user_name)} &bull; ${q.answers ? q.answers.length : 0} answer(s)
                                </div>
                            </div>
                        </button>
                        ${currentUser && currentUser.id == q.user_id ? `
                        <button class="btn btn-sm text-danger position-absolute top-50 end-0 translate-middle-y me-5 delete-question-btn" style="z-index: 10;" data-qid="${q.id}" title="Delete Question">
                            <i class="bi bi-trash"></i>
                        </button>
                        ` : ''}
                    </h2>
                    <div id="faqItem${q.id}" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                        <div class="accordion-body bg-light rounded m-2 p-3">
                            ${q.answers && q.answers.length > 0 ? q.answers.map(a => `
                                <div class="mb-3 pb-2 border-bottom position-relative pe-4">
                                    <div class="fw-medium small">${escapeHtml(a.user_name)}</div>
                                    <div class="text-muted" style="font-size:0.9rem">${escapeHtml(a.answer_text)}</div>
                                    ${currentUser && currentUser.id == a.user_id ? `
                                    <button class="btn btn-sm text-danger position-absolute top-50 end-0 translate-middle-y delete-answer-btn" data-aid="${a.id}" title="Delete Answer">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                    ` : ''}
                                </div>
                            `).join('') : '<div class="text-muted small mb-3">No answers yet.</div>'}
                            
                            <form class="answer-form d-flex gap-2 mt-3" data-qid="${q.id}">
                                <input type="text" name="answer_text" class="form-control form-control-sm" placeholder="Type your answer..." required>
                                <button type="submit" class="btn btn-sm btn-outline-dark">Reply</button>
                            </form>
                            <div class="answer-msg small mt-1" id="ansMsg${q.id}"></div>
                        </div>
                    </div>
                </div>
            `).join("");

            $$(".answer-form", container).forEach(form => {
                form.addEventListener("submit", async e => {
                    e.preventDefault();
                    const userStr = localStorage.getItem('user');
                    if (!userStr) { alert("Please log in to answer."); return; }
                    const user = JSON.parse(userStr);
                    
                    const qid = form.dataset.qid;
                    const ansText = form.querySelector('input[name="answer_text"]').value;
                    const msgEl = $("#ansMsg" + qid);
                    
                    try {
                        await api("/faq/answer", {
                            method: "POST",
                            body: JSON.stringify({
                                question_id: qid,
                                user_id: user.id,
                                user_name: user.name,
                                answer_text: ansText
                            })
                        });
                        form.reset();
                        loadFaqs();
                    } catch (err) {
                        msgEl.innerHTML = `<span class="text-danger">${escapeHtml(err.message)}</span>`;
                    }
                });
            });

            $$(".delete-question-btn", container).forEach(btn => {
                btn.addEventListener("click", async e => {
                    e.stopPropagation();
                    if (!confirm("Are you sure you want to delete this question?")) return;
                    
                    const qid = btn.dataset.qid;
                    try {
                        await api(`/faq/question/${qid}`, {
                            method: "DELETE",
                            body: JSON.stringify({ user_id: currentUser.id })
                        });
                        loadFaqs();
                    } catch (err) {
                        alert("Failed to delete question: " + escapeHtml(err.message));
                    }
                });
            });

            $$(".delete-answer-btn", container).forEach(btn => {
                btn.addEventListener("click", async e => {
                    e.stopPropagation();
                    if (!confirm("Are you sure you want to delete this answer?")) return;
                    
                    const aid = btn.dataset.aid;
                    try {
                        await api(`/faq/answer/${aid}`, {
                            method: "DELETE",
                            body: JSON.stringify({ user_id: currentUser.id })
                        });
                        loadFaqs();
                    } catch (err) {
                        alert("Failed to delete answer: " + escapeHtml(err.message));
                    }
                });
            });

        } catch (err) {
            container.innerHTML = `<div class="text-danger p-3">Failed to load FAQs: ${escapeHtml(err.message)}</div>`;
        }
    }

    const askForm = $("#askQuestionForm");
    if (askForm) {
        askForm.addEventListener("submit", async e => {
            e.preventDefault();
            const userStr = localStorage.getItem('user');
            if (!userStr) { alert("Please log in to ask a question."); return; }
            const user = JSON.parse(userStr);
            
            const qText = $("#newQuestionText").value;
            const msgEl = $("#askQuestionMsg");
            msgEl.innerHTML = `<span class="text-muted">Posting...</span>`;
            
            try {
                await api("/faq/question", {
                    method: "POST",
                    body: JSON.stringify({
                        user_id: user.id,
                        user_name: user.name,
                        question_text: qText
                    })
                });
                askForm.reset();
                msgEl.innerHTML = `<span class="text-success"><i class="bi bi-check-circle"></i> Posted!</span>`;
                setTimeout(() => msgEl.innerHTML = "", 3000);
                loadFaqs();
            } catch (err) {
                msgEl.innerHTML = `<span class="text-danger">${escapeHtml(err.message)}</span>`;
            }
        });
    }

    Promise.all([loadStates(), loadTreks(), loadFaqs()]).catch(err => {
        console.error(err);
        $("#treksGrid").innerHTML = `<div class="col-12"><div class="alert alert-danger">Failed to load treks: ${escapeHtml(err.message)}.</div></div>`;
    });
})();