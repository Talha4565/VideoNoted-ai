// ── State ────────────────────────────────────────────────────────────────
let currentVideoId = null;

// ── DOM helpers ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const show = id => { const el = $(id); if (el) el.classList.remove("hidden"); };
const hide = id => { const el = $(id); if (el) el.classList.add("hidden"); };
function openModal() { const m = $("resultsModal"); if (m) { m.classList.add("open"); document.body.style.overflow = "hidden"; } }
function closeModal() { const m = $("resultsModal"); if (m) { m.classList.remove("open"); document.body.style.overflow = ""; } }
function scrollToSection(id) { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: "smooth" }); }

// ── Entry point ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  $("urlInput").addEventListener("keydown", e => {
    if (e.key === "Enter") processVideo();
  });
});

async function processVideo() {
  const url = $("urlInput").value.trim();

  // Client-side validation
  if (!url) {
    showError("Please paste a YouTube URL.");
    return;
  }
  if (!url.startsWith("http")) {
    showError("Please paste a valid URL starting with http:// or https://");
    return;
  }
  if (!url.includes("youtube.com") && !url.includes("youtu.be")) {
    showError("Please paste a YouTube URL.");
    return;
  }

  clearError();
  hide("resultsSection");
  hide("videoThumb");
  show("loadingState");
  setLoading(true);
  resetLoadingSteps();
  activateStep(1);

  // Animate step progress to give feedback during Gemini processing
  const step2Timer = setTimeout(() => activateStep(2), 3000);
  const step3Timer = setTimeout(() => activateStep(3), 7000);
  const step4Timer = setTimeout(() => activateStep(4), 11000);
  window._loadingTimers = [step2Timer, step3Timer, step4Timer];

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();

    if (!data.success) {
      showError(data.error || "Something went wrong. Please try again.");
      return;
    }

    currentVideoId = data.video_id;
    renderResults(data);

  } catch (err) {
    showError("Network error. Please check your connection and try again.");
  } finally {
    // Clear any pending step timers
    (window._loadingTimers || []).forEach(t => clearTimeout(t));
    window._loadingTimers = [];
    hide("loadingState");
    setLoading(false);
  }
}

// ── Render all result sections ───────────────────────────────────────────
function renderResults(data) {
  // Thumbnail
  if (data.video_id) {
    const thumbImg = $("videoThumbImg");
    thumbImg.src = `https://img.youtube.com/vi/${data.video_id}/mqdefault.jpg`;
    thumbImg.onerror = () => { $("videoThumb").classList.add("hidden"); };
    show("videoThumb");
  }

  // Summary
  $("summaryText").textContent = data.summary || "No summary available.";

  // Key Points
  const kpList = $("keyPointsList");
  kpList.innerHTML = "";
  (data.key_points || []).forEach(point => {
    const li = document.createElement("li");
    li.textContent = point;
    kpList.appendChild(li);
  });

  // Timestamps
  const tsList = $("timestampsList");
  tsList.innerHTML = "";
  (data.timestamps || []).forEach(ts => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="timestamp-badge">${ts.time}</span><span>${ts.note}</span>`;
    tsList.appendChild(li);
  });

  // Takeaways
  const twList = $("takeawaysList");
  twList.innerHTML = "";
  (data.takeaways || []).forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    twList.appendChild(li);
  });

  // Hooks
  const hooksList = $("hooksList");
  hooksList.innerHTML = "";
  (data.hooks || []).forEach(hook => {
    const li = document.createElement("li");
    li.textContent = hook;
    hooksList.appendChild(li);
  });

  // Blog Draft
  $("blogDraftText").textContent = data.blog_draft || "No blog draft available.";

  openModal();
}

// ── Copy to clipboard ────────────────────────────────────────────────────
function copySection(sectionId, btnEl) {
  const el = $(sectionId);
  let text = "";

  if (el.tagName === "UL" || el.tagName === "OL") {
    text = Array.from(el.querySelectorAll("li"))
      .map(li => li.textContent.trim())
      .join("\n");
  } else {
    text = el.textContent.trim();
  }

  navigator.clipboard.writeText(text).then(() => {
    const original = btnEl.textContent;
    btnEl.textContent = "Copied!";
    btnEl.classList.add("copied");
    setTimeout(() => {
      btnEl.textContent = original;
      btnEl.classList.remove("copied");
    }, 2000);
  });
}

// ── Copy All ─────────────────────────────────────────────────────────────
function copyAll() {
  const sections = [
    { label: "SUMMARY", id: "summaryText" },
    { label: "KEY POINTS", id: "keyPointsList" },
    { label: "TIMESTAMPS", id: "timestampsList" },
    { label: "KEY TAKEAWAYS", id: "takeawaysList" },
    { label: "TWITTER / X HOOKS", id: "hooksList" },
    { label: "BLOG DRAFT", id: "blogDraftText" },
  ];

  const divider = "─".repeat(40);
  const parts = sections.map(({ label, id }) => {
    const el = $(id);
    let text = "";
    if (el.tagName === "UL" || el.tagName === "OL") {
      text = Array.from(el.querySelectorAll("li"))
        .map(li => li.textContent.trim())
        .join("\n");
    } else {
      text = el.textContent.trim();
    }
    return `${label}\n${divider}\n${text}`;
  });

  const full = `${"═".repeat(40)}\nVIDEONOTES AI — FULL EXPORT\n${"═".repeat(40)}\n\n` + parts.join("\n\n");

  navigator.clipboard.writeText(full).then(() => {
    const btn = document.querySelector(".btn-copy-all");
    if (!btn) return;
    const orig = btn.textContent;
    btn.textContent = "✅ Copied All!";
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = orig; btn.classList.remove("copied"); }, 2500);
  });
}

// ── Download TXT ─────────────────────────────────────────────────────────
function downloadTxt() {
  if (!currentVideoId) return;
  window.location.href = `/api/export/txt?video_id=${currentVideoId}`;
}

// ── Save as PDF ───────────────────────────────────────────────────────────
function downloadPdf() {
  if (!currentVideoId) return;
  window.open(`/api/export/pdf?video_id=${currentVideoId}`, "_blank");
}

// ── Process another ──────────────────────────────────────────────────
function processAnother() {
  $("urlInput").value = "";
  currentVideoId = null;
  closeModal();
  clearError();
  $("urlInput").focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── UI helpers ───────────────────────────────────────────────────────────
function showError(msg) {
  const el = $("errorMsg");
  el.textContent = msg;
  show("errorMsg");
}

function clearError() {
  hide("errorMsg");
  $("errorMsg").textContent = "";
}

function setLoading(state) {
  const btn = $("generateBtn");
  if (!btn) return;
  btn.disabled = state;
  const loader = btn.querySelector('.btn-loader');
  const text = btn.querySelector('.btn-text');
  const arrow = btn.querySelector('.btn-arrow');
  if (loader) loader.classList.toggle('hidden', !state);
  if (text) text.style.opacity = state ? '0.5' : '1';
  if (arrow) arrow.style.opacity = state ? '0' : '1';
}

function setLoadingMsg(msg) {
  $("loadingMsg").textContent = msg;
}

// ── Loading step tracker ──────────────────────────────────────────────────
function resetLoadingSteps() {
  for (let i = 1; i <= 4; i++) {
    const dot = document.querySelector(`#step${i} .step-dot`);
    if (dot) { dot.classList.remove("active", "done"); }
  }
}

function activateStep(n) {
  // Mark previous steps as done
  for (let i = 1; i < n; i++) {
    const dot = document.querySelector(`#step${i} .step-dot`);
    if (dot) { dot.classList.remove("active"); dot.classList.add("done"); }
  }
  // Activate current step
  const current = document.querySelector(`#step${n} .step-dot`);
  if (current) { current.classList.add("active"); }
  // Update the simple text label too
  const labels = ["Extracting transcript...", "Generating AI summary...", "Building your content...", "Almost done..."];
  setLoadingMsg(labels[n - 1] || "");
}

// ── FAQ accordion ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Navbar scroll
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 40);
  });

  // Mobile menu toggle
  const navToggle = document.getElementById('navToggle');
  const mobileMenu = document.getElementById('mobileMenu');
  if (navToggle && mobileMenu) {
    navToggle.addEventListener('click', () => mobileMenu.classList.toggle('open'));
    document.querySelectorAll('.mobile-link').forEach(link => {
      link.addEventListener('click', () => mobileMenu.classList.remove('open'));
    });
  }

  // FAQ accordion
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });

  // Billing toggle
  const billingToggle = document.getElementById('billingToggle');
  if (billingToggle) {
    let yearly = false;
    billingToggle.addEventListener('click', () => {
      yearly = !yearly;
      billingToggle.classList.toggle('active', yearly);
      document.querySelectorAll('.price-amount').forEach(el => {
        el.textContent = yearly ? el.dataset.yearly : el.dataset.monthly;
      });
      document.querySelectorAll('.toggle-label').forEach(el => {
        el.classList.toggle('active', el.dataset.period === (yearly ? 'yearly' : 'monthly'));
      });
    });
  }

  // Page dots
  const dots = document.querySelectorAll('.dot');
  dots.forEach(dot => {
    dot.addEventListener('click', () => {
      const target = document.getElementById(dot.dataset.section);
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
  });

  // Scroll observer for active dot + nav link
  const sections = document.querySelectorAll('.page');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        dots.forEach(d => d.classList.toggle('active', d.dataset.section === id));
        document.querySelectorAll('.nav-link').forEach(a => a.classList.toggle('active', a.dataset.section === id));
      }
    });
  }, { threshold: 0.5 });
  sections.forEach(s => observer.observe(s));

  // Cursor spotlight
  const spotlight = document.getElementById('cursorSpotlight');
  if (spotlight) {
    document.addEventListener('mousemove', e => {
      spotlight.style.left = e.clientX + 'px';
      spotlight.style.top = e.clientY + 'px';
    });
  }

  // Reveal animations
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

  // Nav link smooth scroll
  document.querySelectorAll('.nav-link[href^="#"], .mobile-link[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) target.scrollIntoView({ behavior: 'smooth' });
      mobileMenu && mobileMenu.classList.remove('open');
    });
  });
});
