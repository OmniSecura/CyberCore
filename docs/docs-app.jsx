/* eslint-disable */
/**
 * CyberCore docs — app shell.
 * Sidebar nav, header, search palette, prev/next, TOC, Tweaks panel.
 */

const { useState, useEffect, useMemo, useRef, useCallback } = React;

/* ---------- icons (header) ---------- */
const HIcons = {
  search:  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="7" cy="7" r="4.5"/><path d="m10.5 10.5 3 3"/></svg>,
  sun:     <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M3 3l1.5 1.5M11.5 11.5 13 13M1 8h2M13 8h2M3 13l1.5-1.5M11.5 4.5 13 3"/></svg>,
  moon:    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M13 9.5A6 6 0 0 1 6.5 3a6 6 0 1 0 6.5 6.5Z"/></svg>,
  github:  <svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 .2a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.5c-2.2.5-2.7-1-2.7-1-.4-.9-.9-1.2-.9-1.2-.7-.5 0-.5 0-.5.8.1 1.2.8 1.2.8.7 1.2 1.9.9 2.4.7.1-.5.3-.9.5-1.1-1.8-.2-3.7-.9-3.7-4 0-.9.3-1.6.8-2.1 0-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.5 7.5 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.4 1.1.1 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.9 3.7-3.7 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 .2Z"/></svg>,
  edit:    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M11 2.5 13.5 5 6 12.5 3 13l.5-3L11 2.5Z"/></svg>,
  arrowR:  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg>,
  arrowL:  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 8H3M7 4 3 8l4 4"/></svg>,
  link:    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9a3 3 0 0 0 4 0l2-2a3 3 0 0 0-4-4l-1 1M10 7a3 3 0 0 0-4 0L4 9a3 3 0 0 0 4 4l1-1"/></svg>,
};

/* ---------- accent palette options ---------- */
const ACCENTS = {
  teal:   { name: "Teal",   light: "oklch(0.66 0.13 195)", dark: "oklch(0.78 0.13 195)", ink: "oklch(0.32 0.08 195)", soft: "oklch(0.94 0.05 195)", line: "oklch(0.85 0.08 195)" },
  amber:  { name: "Amber",  light: "oklch(0.70 0.14 65)",  dark: "oklch(0.82 0.13 65)",  ink: "oklch(0.40 0.10 55)",  soft: "oklch(0.95 0.05 65)",  line: "oklch(0.85 0.08 65)" },
  violet: { name: "Violet", light: "oklch(0.62 0.16 295)", dark: "oklch(0.75 0.16 295)", ink: "oklch(0.36 0.12 295)", soft: "oklch(0.95 0.04 295)", line: "oklch(0.86 0.07 295)" },
  green:  { name: "Green",  light: "oklch(0.62 0.14 150)", dark: "oklch(0.75 0.14 150)", ink: "oklch(0.34 0.10 150)", soft: "oklch(0.94 0.05 150)", line: "oklch(0.85 0.08 150)" },
};

function applyAccent(key, theme) {
  const a = ACCENTS[key] || ACCENTS.teal;
  const root = document.documentElement;
  root.style.setProperty("--accent",      theme === "dark" ? a.dark : a.light);
  root.style.setProperty("--accent-ink",  a.ink);
  root.style.setProperty("--accent-soft", a.soft);
  root.style.setProperty("--accent-line", a.line);
}

/* ---------- search modal ---------- */
function SearchModal({ open, onClose, pages, onPick }) {
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQ(""); setIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return pages.slice(0, 8);
    return pages.filter(p =>
      p.title.toLowerCase().includes(term) ||
      p.group.toLowerCase().includes(term) ||
      (p.lede && p.lede.toLowerCase().includes(term)) ||
      (p.toc || []).some(t => t.toLowerCase().includes(term))
    ).slice(0, 12);
  }, [q, pages]);

  useEffect(() => { setIdx(0); }, [q]);

  if (!open) return null;

  const onKey = (e) => {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowDown") { e.preventDefault(); setIdx(i => Math.min(results.length - 1, i + 1)); }
    else if (e.key === "ArrowUp")   { e.preventDefault(); setIdx(i => Math.max(0, i - 1)); }
    else if (e.key === "Enter")     { const r = results[idx]; if (r) { onPick(r.id); onClose(); } }
  };

  return (
    <div className="kmodal-back" onClick={(e) => { if (e.target.classList.contains("kmodal-back")) onClose(); }}>
      <div className="kmodal" onKeyDown={onKey}>
        <input
          ref={inputRef}
          className="kmodal-input"
          placeholder="Search docs — services, configuration, SDKs…"
          value={q}
          onChange={e => setQ(e.target.value)}
        />
        <div className="kmodal-list">
          {results.length === 0 && <div className="kmodal-empty">No matches for "{q}".</div>}
          {results.map((r, i) => (
            <div
              key={r.id}
              className={`kmodal-item ${i === idx ? "active" : ""}`}
              onMouseEnter={() => setIdx(i)}
              onClick={() => { onPick(r.id); onClose(); }}
            >
              <span className="ki-icon">
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" width="13" height="13">
                  {r.icon}
                </svg>
              </span>
              <div className="ki-text">
                <div className="ki-title">{r.title}</div>
                <div className="ki-sub">{r.group.toLowerCase()} / {r.id}</div>
              </div>
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" width="13" height="13" style={{ color: "var(--mute)" }}>
                <path d="M3 8h10M9 4l4 4-4 4"/>
              </svg>
            </div>
          ))}
        </div>
        <div className="kmodal-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>esc</kbd> close</span>
          <span style={{ marginLeft: "auto" }}>{results.length} result{results.length === 1 ? "" : "s"}</span>
        </div>
      </div>
    </div>
  );
}

/* ---------- sidebar ---------- */
function Sidebar({ pages, groups, current, onNav }) {
  return (
    <aside className="sidebar">
      {groups.map((g, gi) => {
        const groupPages = pages.filter(p => p.group === g);
        if (groupPages.length === 0) return null;
        return (
          <div className="side-section" key={g}>
            <div className="side-section-title">
              <span className="num">0{gi + 1}</span>
              <span>{g}</span>
            </div>
            {groupPages.map(p => (
              <a
                key={p.id}
                className={`side-link ${current === p.id ? "active" : ""}`}
                onClick={() => onNav(p.id)}
              >
                <span className="icon">
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    {p.icon}
                  </svg>
                </span>
                <span>{p.title}</span>
                {p.pillNew && <span className="new-pill">new</span>}
              </a>
            ))}
          </div>
        );
      })}
    </aside>
  );
}

/* ---------- TOC ---------- */
function Toc({ items, contentRef, pageId }) {
  const [active, setActive] = useState(items[0] || "");

  useEffect(() => {
    if (!contentRef.current || items.length === 0) return;
    const headings = items
      .map(t => contentRef.current.querySelector(`#${slug(t)}`))
      .filter(Boolean);
    if (headings.length === 0) return;

    const obs = new IntersectionObserver(
      entries => {
        const vis = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.textContent);
      },
      { rootMargin: "-80px 0px -65% 0px", threshold: [0, 1] }
    );
    headings.forEach(h => obs.observe(h));
    return () => obs.disconnect();
  }, [items, pageId]);

  if (items.length === 0) return (
    <aside className="toc">
      <div className="toc-aux">
        <a href="https://github.com/OmniSecura/CyberCore" target="_blank" rel="noopener">
          <svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 .2a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.5c-2.2.5-2.7-1-2.7-1-.4-.9-.9-1.2-.9-1.2-.7-.5 0-.5 0-.5.8.1 1.2.8 1.2.8.7 1.2 1.9.9 2.4.7.1-.5.3-.9.5-1.1-1.8-.2-3.7-.9-3.7-4 0-.9.3-1.6.8-2.1 0-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.5 7.5 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.4 1.1.1 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.9 3.7-3.7 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 .2Z"/></svg>
          View on GitHub
        </a>
        <a href="#" onClick={(e) => { e.preventDefault(); navigator.clipboard.writeText(window.location.href); }}>
          {HIcons.link}
          Copy page link
        </a>
      </div>
    </aside>
  );
  return (
    <aside className="toc">
      <div className="toc-title">On this page</div>
      <ul className="toc-list">
        {items.map(t => (
          <li key={t}>
            <a href={`#${slug(t)}`} className={active === t ? "active" : ""}>{t}</a>
          </li>
        ))}
      </ul>
      <div className="toc-aux">
        <a href={`https://github.com/OmniSecura/CyberCore/edit/main/docs/${pageId}.md`} target="_blank" rel="noopener">
          {HIcons.edit}
          Edit this page
        </a>
        <a href="#" onClick={(e) => { e.preventDefault(); navigator.clipboard.writeText(window.location.href); }}>
          {HIcons.link}
          Copy page link
        </a>
      </div>
    </aside>
  );
}

const slug = (s) => (s || "")
  .toLowerCase()
  .replace(/&amp;/g, "&")
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-|-$/g, "");

/* ---------- main app ---------- */
function App() {
  const PAGES = window.PAGES;
  const GROUPS = window.GROUPS;

  const [pageId, setPageId] = useState(() => {
    const hash = window.location.hash.replace(/^#/, "");
    return PAGES.find(p => p.id === hash) ? hash : "welcome";
  });
  const [searchOpen, setSearchOpen] = useState(false);
  const contentRef = useRef(null);
  const scrollRef = useRef(null);

  const tweaks = window.TWEAK_DEFAULTS || {};
  const [theme, setTheme] = useState(tweaks.theme || "light");
  const [accent, setAccent] = useState(tweaks.accent || "teal");
  const [density, setDensity] = useState(tweaks.density || "comfortable");

  // apply theme + accent
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    applyAccent(accent, theme);
  }, [theme, accent]);

  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
  }, [density]);

  const nav = useCallback((id) => {
    setPageId(id);
    window.history.replaceState(null, "", `#${id}`);
    // scroll to top of content
    requestAnimationFrame(() => {
      window.scrollTo({ top: 0, behavior: "instant" });
    });
  }, []);

  // expose for inline page links
  useEffect(() => { window.__nav = nav; }, [nav]);

  // hash routing
  useEffect(() => {
    const onHash = () => {
      const id = window.location.hash.replace(/^#/, "");
      if (id && PAGES.find(p => p.id === id) && id !== pageId) setPageId(id);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [pageId]);

  // cmd+k
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(o => !o);
      } else if (e.key === "/" && !["INPUT","TEXTAREA"].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // wrap headings with ids (for in-page anchors + TOC) + measure reading time
  const [readMin, setReadMin] = useState(2);
  useEffect(() => {
    if (!contentRef.current) return;
    const headings = contentRef.current.querySelectorAll("h2, h3");
    headings.forEach(h => {
      if (!h.id) h.id = slug(h.textContent);
    });
    setReadMin(readingTime(null, contentRef.current));
  }, [pageId]);

  const page = PAGES.find(p => p.id === pageId) || PAGES[0];
  const PageBody = page.body;

  const flatPages = PAGES;
  const i = flatPages.findIndex(p => p.id === page.id);
  const prev = i > 0 ? flatPages[i - 1] : null;
  const next = i < flatPages.length - 1 ? flatPages[i + 1] : null;

  return (
    <>
      <header className="header">
        <div className="header-left">
          <a className="brand" onClick={() => nav("welcome")}>
            <span className="brand-mark">CC</span>
            <span>CyberCore</span>
            <span className="brand-version">docs · 0.4</span>
          </a>
        </div>
        <div className="header-right">
          <div className="search" onClick={() => setSearchOpen(true)}>
            {HIcons.search}
            <span>Search docs…</span>
            <kbd>⌘K</kbd>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <nav style={{ display: "flex", alignItems: "center", gap: 2 }}>
              <a className="header-link" aria-current="true">Docs</a>
              <a className="header-link" href="https://github.com/OmniSecura/CyberCore" target="_blank" rel="noopener">Changelog</a>
              <a className="header-link" href="https://github.com/OmniSecura/CyberCore" target="_blank" rel="noopener">API</a>
            </nav>
            <div className="header-tools">
              <button className="icon-btn" title="Toggle theme" onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}>
                {theme === "dark" ? HIcons.sun : HIcons.moon}
              </button>
              <a className="icon-btn" href="https://github.com/OmniSecura/CyberCore" target="_blank" rel="noopener" title="GitHub">
                {HIcons.github}
              </a>
            </div>
          </div>
        </div>
      </header>

      <div className="app">
        <Sidebar pages={PAGES} groups={GROUPS} current={page.id} onNav={nav} />
        <div className="main">
          <article className="content" ref={scrollRef} data-screen-label={`Docs · ${page.title}`}>
            <div className="content-inner" ref={contentRef}>
              <div className="breadcrumbs">
                <span>docs</span>
                <span className="sep">/</span>
                <span>{page.group.toLowerCase()}</span>
                <span className="sep">/</span>
                <span className="here">{page.id}</span>
              </div>
              <h1 className="doc-title">{page.title}</h1>
              {page.lede && <p className="doc-lede">{page.lede}</p>}
              <div className="doc-meta">
                <span className="meta-item">
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="8" r="6"/><path d="M8 4v4l3 2"/></svg>
                  Updated May 12, 2026
                </span>
                <span className="dot"></span>
                <span className="meta-item">{readMin} min read</span>
                <span className="dot"></span>
                <span className="meta-item">
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"><path d="M2 4h12M2 8h12M2 12h7"/></svg>
                  {page.group}
                </span>
              </div>

              <PageBody />

              <div className="page-foot">
                {prev ? (
                  <a className="page-nav" onClick={() => nav(prev.id)}>
                    <div className="pn-lab">{HIcons.arrowL}Previous</div>
                    <div className="pn-title">{prev.title}</div>
                  </a>
                ) : <span />}
                {next ? (
                  <a className="page-nav next" onClick={() => nav(next.id)}>
                    <div className="pn-lab">Next{HIcons.arrowR}</div>
                    <div className="pn-title">{next.title}</div>
                  </a>
                ) : <span />}
              </div>

              <div className="last-updated">
                last updated · 2026-05-12 · commit af36423 · MIT license
              </div>
            </div>
          </article>
          <Toc items={page.toc || []} contentRef={contentRef} pageId={page.id} />
        </div>
      </div>

      <SearchModal
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        pages={PAGES}
        onPick={(id) => nav(id)}
      />

      <TweaksHost
        theme={theme} setTheme={setTheme}
        accent={accent} setAccent={setAccent}
        density={density} setDensity={setDensity}
      />
    </>
  );
}

// reading time — measured from the rendered DOM after mount,
// falls back to a sensible default for the initial render.
function readingTime(page, contentEl) {
  if (contentEl) {
    const words = (contentEl.innerText || "").trim().split(/\s+/).filter(Boolean).length;
    if (words > 0) return Math.max(1, Math.round(words / 220));
  }
  return 2;
}

/* ---------- Tweaks host ---------- */
function TweaksHost({ theme, setTheme, accent, setAccent, density, setDensity }) {
  if (!window.TweaksPanel) return null;
  const { TweaksPanel, TweakSection, TweakRadio, TweakSelect } = window;

  const setT = (patch) => {
    if (typeof patch !== "object") return;
    if ("theme" in patch) setTheme(patch.theme);
    if ("accent" in patch) setAccent(patch.accent);
    if ("density" in patch) setDensity(patch.density);
    try {
      window.parent.postMessage({ type: "__edit_mode_set_keys", edits: patch }, "*");
    } catch {}
  };

  return (
    <TweaksPanel title="Tweaks">
      <TweakSection title="Theme">
        <TweakRadio
          label="Mode"
          value={theme}
          onChange={(v) => setT({ theme: v })}
          options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }]}
        />
      </TweakSection>
      <TweakSection title="Accent">
        <TweakSelect
          label="Color"
          value={accent}
          onChange={(v) => setT({ accent: v })}
          options={[
            { value: "teal",   label: "Teal" },
            { value: "amber",  label: "Amber" },
            { value: "violet", label: "Violet" },
            { value: "green",  label: "Green" },
          ]}
        />
      </TweakSection>
      <TweakSection title="Density">
        <TweakRadio
          label="Spacing"
          value={density}
          onChange={(v) => setT({ density: v })}
          options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]}
        />
      </TweakSection>
    </TweaksPanel>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
