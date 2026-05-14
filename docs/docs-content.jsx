/* eslint-disable */
/**
 * CyberCore docs — page content.
 *
 * Adding a new page: append an object to PAGES with { id, group, title, lede, icon, body }.
 * `body` is a function returning JSX. Use the helpers (Code, Callout, Table, Card, etc.)
 * for consistent styling. Headings inside `body` should be h2/h3 with stable ids — the
 * TOC reads them automatically.
 */

const { useState } = React;

/* ---------- helpers ---------- */

const Code = ({ lang, file, children, copyable = true }) => {
  const [copied, setCopied] = useState(false);
  const onCopy = () => {
    const text = (typeof children === "string" ? children : (children?.props?.children ?? "")) + "";
    try {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {}
  };
  return (
    <div className="code">
      <div className="code-header">
        <span className="lang">{file || lang}</span>
        {copyable && (
          <button className="code-copy" onClick={onCopy}>
            {copied ? "copied" : "copy"}
          </button>
        )}
      </div>
      <pre><code>{children}</code></pre>
    </div>
  );
};

// minimal "highlighter": wraps known tokens in spans
const hl = (s, rules) => {
  // rules is array of {re, cls}
  let parts = [{ t: s, c: null }];
  rules.forEach(({ re, cls }) => {
    parts = parts.flatMap(p => {
      if (p.c) return [p];
      const out = [];
      let last = 0;
      const str = p.t;
      str.replace(re, (m, ...rest) => {
        const idx = rest[rest.length - 2];
        if (idx > last) out.push({ t: str.slice(last, idx), c: null });
        out.push({ t: m, c: cls });
        last = idx + m.length;
        return m;
      });
      if (last < str.length) out.push({ t: str.slice(last), c: null });
      return out;
    });
  });
  return parts.map((p, i) => p.c ? <span key={i} className={p.c}>{p.t}</span> : p.t);
};

const Py = ({ children }) => hl(children, [
  { re: /#[^\n]*/g, cls: "c" },
  { re: /"[^"]*"|'[^']*'/g, cls: "s" },
  { re: /\b(from|import|as|def|class|return|if|else|elif|for|while|try|except|with|in|not|is|and|or|None|True|False|lambda|pass|raise|yield)\b/g, cls: "k" },
  { re: /\b([A-Z][A-Za-z0-9_]+)\b/g, cls: "f" },
  { re: /\b\d+(\.\d+)?\b/g, cls: "n" },
]);

const Js = ({ children }) => hl(children, [
  { re: /\/\/[^\n]*/g, cls: "c" },
  { re: /`[^`]*`|"[^"]*"|'[^']*'/g, cls: "s" },
  { re: /\b(import|from|export|const|let|var|function|return|if|else|for|while|new|class|extends|async|await|try|catch|finally|throw|null|undefined|true|false)\b/g, cls: "k" },
  { re: /\b([A-Z][A-Za-z0-9_]+)\b/g, cls: "f" },
  { re: /\b\d+(\.\d+)?\b/g, cls: "n" },
]);

const Sh = ({ children }) => hl(children, [
  { re: /#[^\n]*/g, cls: "c" },
  { re: /"[^"]*"|'[^']*'/g, cls: "s" },
  { re: /\b(docker|compose|git|cd|cp|helm|install|kubectl|export|sudo|curl|bash|sh)\b/g, cls: "k" },
  { re: /\b\d+\b/g, cls: "n" },
  { re: /--[a-zA-Z\-]+/g, cls: "f" },
]);

const Json = ({ children }) => hl(children, [
  { re: /"[^"]*"(?=\s*:)/g, cls: "k" },
  { re: /"[^"]*"/g, cls: "s" },
  { re: /\b\d+(\.\d+)?\b/g, cls: "n" },
  { re: /\b(true|false|null)\b/g, cls: "n" },
]);

const Yaml = ({ children }) => hl(children, [
  { re: /#[^\n]*/g, cls: "c" },
  { re: /^[\s-]*[a-zA-Z_][\w-]*(?=:)/gm, cls: "k" },
  { re: /"[^"]*"|'[^']*'/g, cls: "s" },
  { re: /\b\d+\b/g, cls: "n" },
]);

const Callout = ({ kind = "info", title, children }) => {
  const icons = {
    info:    <path d="M8 8v4M8 5v.01M14 8A6 6 0 1 1 2 8a6 6 0 0 1 12 0Z" />,
    warn:    <path d="M8 5.5v3M8 11v.01M1.6 13h12.8a1 1 0 0 0 .87-1.5L8.87 1.4a1 1 0 0 0-1.74 0L.74 11.5A1 1 0 0 0 1.6 13Z" />,
    danger:  <path d="M8 5.5v3M8 11v.01M14 8A6 6 0 1 1 2 8a6 6 0 0 1 12 0Z" />,
    success: <path d="m4 8 2.5 2.5L12 5M14 8A6 6 0 1 1 2 8a6 6 0 0 1 12 0Z" />,
  };
  return (
    <div className="callout" data-kind={kind}>
      <span className="callout-icon">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
          {icons[kind]}
        </svg>
      </span>
      <div className="callout-body">
        {title && <span className="callout-title">{title}</span>}
        {children}
      </div>
    </div>
  );
};

const SideIcons = {
  home:    <path d="M2 8 8 3l6 5v6a1 1 0 0 1-1 1h-3v-4H7v4H4a1 1 0 0 1-1-1V8H2Z" />,
  rocket:  <path d="M5 11c-1 0-2 1-2 3 2 0 3-1 3-2M9 7 5 11l-1-1 4-4M11 5l-4 4-2-2 4-4 2 2ZM11 5l2-2M9 3l2-2" />,
  arch:    <path d="M2 13h12M3 13V8h3v5M7 13V3h2v10M10 13V6h3v7" />,
  shield:  <path d="M8 1 2 3v5c0 4 3 6.5 6 7 3-.5 6-3 6-7V3L8 1Z" />,
  scan:    <path d="M2 4V2h2M14 4V2h-2M2 12v2h2M14 12v2h-2M5 8h6" />,
  sast:    <path d="m4 5-3 3 3 3M12 5l3 3-3 3M10 3 6 13" />,
  dast:    <path d="M8 2v3M8 11v3M2 8h3M11 8h3M5 5 3 3M11 5l2-2M5 11l-2 2M11 11l2 2M8 6a2 2 0 1 1 0 4 2 2 0 0 1 0-4Z" />,
  log:     <path d="M3 2h7l3 3v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1ZM10 2v3h3M5 8h6M5 11h5" />,
  agent:   <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" />,
  alert:   <path d="M8 1.5C5 1.5 3 4 3 7v3l-1 1.5h12L13 10V7c0-3-2-5.5-5-5.5ZM6.5 13.5a1.5 1.5 0 0 0 3 0" />,
  sdk:     <path d="m3 4 3 4-3 4M8 12h5" />,
  cog:     <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z M8 1v2M8 13v2M3.5 3.5l1.4 1.4M11.1 11.1l1.4 1.4M1 8h2M13 8h2M3.5 12.5l1.4-1.4M11.1 4.9l1.4-1.4" />,
  deploy:  <path d="M3 13h10M5 10V4a3 3 0 0 1 6 0v6M5 7h6" />,
  map:     <path d="M6 2 2 4v10l4-2 4 2 4-2V2l-4 2-4-2ZM6 2v10M10 4v10" />,
  heart:   <path d="M8 13s-5-3-5-7a3 3 0 0 1 5-2 3 3 0 0 1 5 2c0 4-5 7-5 7Z" />,
};

/* ---------- pages ---------- */

const Welcome = () => (
  <>
    <div className="hero">
      <div className="hero-eyebrow">
        <span className="ver">v0.4 · BETA</span>
        <span>Released 12 May 2026</span>
      </div>
      <h1>Run your own security operations center.</h1>
      <p className="lede">
        CyberCore is a self-hosted, modular cybersecurity platform — code scanning,
        live application testing, system telemetry, and log management — deployable on
        your own infrastructure in minutes, without sending data to third parties.
      </p>
      <div className="hero-cta">
        <a className="btn" data-page="quick-start" onClick={(e)=>{e.preventDefault(); window.__nav('quick-start');}}>
          Quick start
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8h10M9 4l4 4-4 4"/></svg>
        </a>
        <a className="btn ghost" href="https://github.com/OmniSecura/CyberCore" target="_blank" rel="noopener">
          <svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 .2a8 8 0 0 0-2.5 15.6c.4.1.5-.2.5-.4v-1.5c-2.2.5-2.7-1-2.7-1-.4-.9-.9-1.2-.9-1.2-.7-.5 0-.5 0-.5.8.1 1.2.8 1.2.8.7 1.2 1.9.9 2.4.7.1-.5.3-.9.5-1.1-1.8-.2-3.7-.9-3.7-4 0-.9.3-1.6.8-2.1 0-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.5 7.5 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.4 1.1.1 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3.1-1.9 3.7-3.7 4 .3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A8 8 0 0 0 8 .2Z"/></svg>
          View on GitHub
        </a>
      </div>
    </div>

    <h2 id="status">Project status</h2>
    <p>CyberCore is in active development. The core stack is stable; some modules are still maturing.</p>
    <div className="status-row">
      <div className="stat">
        <div className="stat-label">Stack version</div>
        <div className="stat-value">0.4.2</div>
        <div className="stat-sub">released 2026-05-12</div>
      </div>
      <div className="stat">
        <div className="stat-label">Services</div>
        <div className="stat-value">8 / 8</div>
        <div className="stat-sub"><span className="ok">● all online</span></div>
      </div>
      <div className="stat">
        <div className="stat-label">Scanners shipped</div>
        <div className="stat-value">8</div>
        <div className="stat-sub">SAST + DAST</div>
      </div>
      <div className="stat">
        <div className="stat-label">License</div>
        <div className="stat-value">MIT</div>
        <div className="stat-sub">commercial OK</div>
      </div>
    </div>

    <h2 id="start-here">Start here</h2>
    <div className="card-grid">
      <a className="card" onClick={()=>window.__nav('quick-start')}>
        <div className="card-eyebrow"><span>01</span> · Get running</div>
        <div className="card-title">Quick start</div>
        <div className="card-desc">Boot the core stack with Docker Compose in under five minutes.</div>
        <div className="card-arrow">Read guide ›</div>
      </a>
      <a className="card" onClick={()=>window.__nav('architecture')}>
        <div className="card-eyebrow"><span>02</span> · Understand</div>
        <div className="card-title">Architecture</div>
        <div className="card-desc">How services, workers, agents and the dashboard fit together.</div>
        <div className="card-arrow">See the map ›</div>
      </a>
      <a className="card" onClick={()=>window.__nav('sast-service')}>
        <div className="card-eyebrow"><span>03</span> · Scan code</div>
        <div className="card-title">SAST service</div>
        <div className="card-desc">Eight static analyzers, language detection, unified findings.</div>
        <div className="card-arrow">Open docs ›</div>
      </a>
      <a className="card" onClick={()=>window.__nav('log-service')}>
        <div className="card-eyebrow"><span>04</span> · Collect logs</div>
        <div className="card-title">Log service</div>
        <div className="card-desc">Project-isolated log ingestion with Python, JS and Go SDKs.</div>
        <div className="card-arrow">Open docs ›</div>
      </a>
    </div>

    <h2 id="what-you-get">What you get out of the box</h2>
    <ul>
      <li><strong>Static code analysis</strong> across Python, JS/TS, Go, Java, PHP, Ruby, C, Rust and IaC.</li>
      <li><strong>Dynamic application testing</strong> built on OWASP ZAP — crawling, injection, XSS, SSRF, header & TLS audits.</li>
      <li><strong>Centralized logging</strong> with project-based isolation, structured metadata, and webhook alerts.</li>
      <li><strong>Host telemetry</strong> from a lightweight C++ agent feeding an ML anomaly engine.</li>
      <li><strong>Unified alerting</strong> over email, Slack, Discord, Telegram and webhooks, with dedup and escalation.</li>
    </ul>

    <Callout kind="info" title="Self-hosted by default.">
      No data leaves your infrastructure. CyberCore is designed for teams that need GDPR
      alignment, air-gapped deployments, or simply don't want a third-party SaaS holding
      their findings.
    </Callout>
  </>
);

const QuickStart = () => (
  <>
    <h2 id="prerequisites">Prerequisites</h2>
    <ul>
      <li>Docker 24+ and Docker Compose v2</li>
      <li>8 GB RAM minimum — 16 GB recommended for the full stack</li>
      <li>Git, and a free TCP port on <code>3000</code> for the dashboard</li>
    </ul>

    <h2 id="clone">1. Clone &amp; configure</h2>
    <Code lang="bash" file="terminal"><Sh>{`git clone https://github.com/OmniSecura/CyberCore.git
cd CyberCore

cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET, etc.`}</Sh></Code>

    <Callout kind="warn" title="Don't ship the defaults.">
      The bundled <code>.env.example</code> uses obvious placeholder secrets. Generate a
      64-character random string for <code>JWT_SECRET</code> before exposing the stack
      to anything beyond <code>localhost</code>.
    </Callout>

    <h2 id="profiles">2. Pick a profile</h2>
    <p>CyberCore ships three Compose profiles. Start with <code>core</code> and add what you need.</p>

    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Profile</th><th>What boots</th><th>RAM</th></tr></thead>
        <tbody>
          <tr>
            <td><code>core</code></td>
            <td>Auth · tenant · dashboard · Postgres · Redis</td>
            <td>~3 GB</td>
          </tr>
          <tr>
            <td><code>scanning</code></td>
            <td>+ scan-service · SAST · DAST · scan-worker</td>
            <td>~6 GB</td>
          </tr>
          <tr>
            <td><code>full</code></td>
            <td>Everything: logs · agent · ML · Kafka · TimescaleDB</td>
            <td>~12 GB</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 id="run">3. Run it</h2>
    <Code lang="bash" file="terminal"><Sh>{`# Just the core stack
docker compose --profile core up

# Add scanning
docker compose --profile core --profile scanning up

# Or run everything
docker compose --profile full up`}</Sh></Code>

    <h2 id="first-login">4. First login</h2>
    <ol>
      <li>Open <code>http://localhost:3000</code></li>
      <li>The first registered user becomes the tenant owner — pick a strong password (12+ chars, mixed case, number, symbol).</li>
      <li>Enable MFA from <strong>Settings → Security</strong> before inviting anyone else.</li>
      <li>Create your first project from the dashboard to generate an API key for the log SDK.</li>
    </ol>

    <Callout kind="success" title="You're live.">
      That's it — the dashboard is yours. From here you can plug in the <a onClick={()=>window.__nav('log-service')}>Log SDK</a>,
      launch a <a onClick={()=>window.__nav('sast-service')}>SAST scan</a>, or roll out the
      <a onClick={()=>window.__nav('agent-service')}> system agent</a>.
    </Callout>
  </>
);

const Architecture = () => (
  <>
    <p>CyberCore is a constellation of independently-deployable services. Use only what you need; each profile boots a different slice.</p>

    <div className="arch">
      <div className="arch-row">
        <div className="arch-label">Edge</div>
        <div className="arch-items">
          <span className="arch-box"><span className="dot"></span>dashboard <span style={{color:"var(--mute)"}}>· React</span></span>
          <span className="arch-box muted"><span className="dot"></span>SDKs · cyberlog</span>
        </div>
      </div>
      <div className="arch-row">
        <div className="arch-label">Services</div>
        <div className="arch-items">
          <span className="arch-box"><span className="dot"></span>auth-service</span>
          <span className="arch-box"><span className="dot"></span>tenant-service</span>
          <span className="arch-box"><span className="dot"></span>organization-service</span>
          <span className="arch-box"><span className="dot"></span>scan-service</span>
          <span className="arch-box"><span className="dot"></span>sast-service</span>
          <span className="arch-box"><span className="dot"></span>dast-service</span>
          <span className="arch-box"><span className="dot"></span>log-service</span>
          <span className="arch-box"><span className="dot"></span>agent-service</span>
          <span className="arch-box"><span className="dot"></span>alert-service</span>
        </div>
      </div>
      <div className="arch-row">
        <div className="arch-label">Workers</div>
        <div className="arch-items">
          <span className="arch-box"><span className="dot"></span>scan-worker · Celery</span>
          <span className="arch-box"><span className="dot"></span>log-consumer · Kafka → Timescale</span>
          <span className="arch-box"><span className="dot"></span>ml-worker · anomaly engine</span>
        </div>
      </div>
      <div className="arch-row">
        <div className="arch-label">Agent</div>
        <div className="arch-items">
          <span className="arch-box"><span className="dot"></span>core · C++ sniffer</span>
          <span className="arch-box"><span className="dot"></span>orchestrator · Python</span>
        </div>
      </div>
      <div className="arch-row">
        <div className="arch-label">Storage</div>
        <div className="arch-items">
          <span className="arch-box muted"><span className="dot"></span>PostgreSQL</span>
          <span className="arch-box muted"><span className="dot"></span>TimescaleDB</span>
          <span className="arch-box muted"><span className="dot"></span>Redis</span>
          <span className="arch-box muted"><span className="dot"></span>Kafka</span>
        </div>
      </div>
    </div>

    <h2 id="data-flow">Data flow</h2>
    <p>Every signal — a SAST finding, a DAST alert, an agent anomaly — converges on the <strong>scan-service</strong>, which normalizes it into a single shape before fan-out to the dashboard and alert pipeline.</p>

    <ol>
      <li><strong>Producers</strong> (workers, agents, SDK clients) emit raw events.</li>
      <li><strong>scan-service</strong> normalizes severity, deduplicates, attaches project &amp; tenant metadata.</li>
      <li><strong>alert-service</strong> decides who hears about it and through which channel.</li>
      <li><strong>dashboard</strong> reads the normalized stream — one UI regardless of source.</li>
    </ol>

    <h2 id="independence">Component independence</h2>
    <p>Each service ships its own Dockerfile, Helm chart, and database migration set. You can run the log-service standalone and ignore scanning entirely — or vice versa. The dashboard gracefully hides modules whose backend isn't up.</p>

    <Callout kind="info" title="Why FastAPI everywhere?">
      All Python services use a shared <code>cybercore-commons</code> package that pins
      Pydantic schemas, error codes and HTTP middleware. Adding a new service means
      <code>cookiecutter</code>-ing the template and registering routes — the rest is wired.
    </Callout>
  </>
);

const AuthService = () => (
  <>
    <p>Identity is the front door. <code>auth-service</code> handles registration, login, MFA, OAuth federation, and JWT session management for every other module in the platform.</p>

    <h2 id="registration">Registration</h2>
    <ul>
      <li>Email, first name, last name</li>
      <li>Password entered twice — confirmation is enforced server-side, not just in the UI</li>
      <li>Strong policy: <strong>≥12 chars</strong>, uppercase, lowercase, number, special character</li>
      <li>Every user receives a unique UUID at registration time, used as the stable foreign key throughout the platform</li>
    </ul>

    <h2 id="mfa">Multi-factor authentication</h2>
    <p>TOTP-based, compatible with Google Authenticator, Authy, 1Password, and any RFC 6238 client. Enabled per-user from the dashboard; tenants can mark MFA as required for the whole organization.</p>

    <Code lang="http" file="POST /v1/auth/mfa/enroll"><Json>{`{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_uri": "otpauth://totp/CyberCore:alice@example.com?secret=...&issuer=CyberCore",
  "recovery_codes": ["a1b2-c3d4-e5f6", "..."]
}`}</Json></Code>

    <h2 id="oauth">OAuth2 / social login</h2>
    <p>Google and GitHub are wired in. Adding a provider is one config block — the service uses Authlib under the hood.</p>

    <h2 id="sessions">Sessions &amp; tokens</h2>
    <ul>
      <li>JWT access tokens (15 min) + refresh tokens (7 days) with rotation</li>
      <li>Refresh-token reuse triggers automatic session revocation</li>
      <li>Tokens are scoped to a tenant + role — see <a onClick={()=>window.__nav('tenant-service')}>tenant-service</a></li>
    </ul>

    <h2 id="brute-force">Brute-force protection</h2>
    <ul>
      <li>Per-IP rate limiting on <code>/login</code>, <code>/register</code>, <code>/mfa/verify</code></li>
      <li>Account lockout after 5 failed attempts in 15 minutes</li>
      <li>Email notification on lockout, plus an audit-log entry the admin can review</li>
    </ul>

    <Callout kind="warn" title="Don't disable MFA enforcement.">
      The tenant-level <code>require_mfa</code> flag exists for a reason. The first
      breach class CyberCore sees in production deployments is a self-hosted instance
      with a weak admin password and no second factor.
    </Callout>
  </>
);

const ScanService = () => (
  <>
    <p>The unified scan orchestrator. Every finding — whether it came from Semgrep, ZAP, or the host agent — is normalized here before anything else in the platform sees it.</p>

    <h2 id="unified-format">Unified finding format</h2>
    <p>Severity, location, remediation, confidence — one shape, regardless of the underlying tool.</p>

    <Code lang="json" file="finding.json"><Json>{`{
  "scan_id": "uuid",
  "scan_type": "SAST | DAST | AGENT",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW | INFO",
  "title": "SQL Injection in user input handler",
  "description": "User-supplied input concatenated into a raw SQL query.",
  "location": { "file": "app/db.py", "line": 42 },
  "remediation": "Use parameterized queries",
  "tool": "semgrep",
  "confidence": 0.93,
  "created_at": "2026-05-12T14:08:00Z"
}`}</Json></Code>

    <h2 id="example">Example finding (rendered)</h2>
    <p>This is what a unified finding looks like once the dashboard picks it up.</p>

    <div className="finding">
      <div className="finding-head">
        <span className="sev" data-level="critical">critical</span>
        <span className="finding-title">SQL Injection in user input handler</span>
        <span className="finding-meta">semgrep · 0.93 conf</span>
      </div>
      <p style={{margin:"0 0 8px", color:"var(--mute)", fontSize:13}}>
        User-supplied input is concatenated directly into a raw SQL query, allowing an
        attacker to manipulate query semantics.
      </p>
      <div className="finding-loc">app/db.py · line 42</div>
      <div className="finding-rem">
        <strong>Remediation —</strong> Use parameterized queries via the
        ORM, or pass values as bind parameters to the cursor.
      </div>
    </div>

    <h2 id="severities">Severity normalization</h2>
    <p>Every upstream tool ranks differently. The scan-service maps them all to a single 5-level scale:</p>
    <div style={{display:"flex", gap:8, flexWrap:"wrap", margin:"16px 0 24px"}}>
      <span className="sev" data-level="critical">critical</span>
      <span className="sev" data-level="high">high</span>
      <span className="sev" data-level="medium">medium</span>
      <span className="sev" data-level="low">low</span>
      <span className="sev" data-level="info">info</span>
    </div>

    <h2 id="dedup">Deduplication</h2>
    <p>The same vulnerability detected by two tools is collapsed into one finding with both <code>tool</code> attributions. Dedup keys are content-addressable: <code>hash(rule_id + normalized_location + scope)</code>.</p>

    <Callout kind="info" title="Re-scans don't multiply.">
      Scanning the same project repeatedly creates a single canonical finding per issue,
      with a status history (open → fixed → regressed). Your dashboard does not turn into
      a tape parade.
    </Callout>
  </>
);

const SastService = () => (
  <>
    <p>Static Application Security Testing — finds vulnerabilities in source code before it runs. Eight tools, automatic language detection, deduplicated results.</p>

    <h2 id="inputs">Input methods</h2>
    <ul>
      <li>Upload a <strong>ZIP archive</strong> of your project from the dashboard</li>
      <li>Provide a <strong>public Git repository URL</strong> — the service shallow-clones it</li>
      <li>Trigger from CI via the REST API (see below)</li>
    </ul>

    <h2 id="tools">Tools shipped</h2>
    <p>Every scan runs all applicable tools automatically — language detection happens upfront so only relevant analyzers execute.</p>

    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Tool</th><th>Languages</th><th>Catches</th></tr></thead>
        <tbody>
          <tr>
            <td className="tool-name">Semgrep</td>
            <td>Python · JS/TS · Go · Java · PHP · Ruby · C · Rust</td>
            <td>OWASP Top 10, secrets, framework rules (Django, Flask, Express)</td>
          </tr>
          <tr>
            <td className="tool-name">Bandit</td>
            <td>Python</td>
            <td>Deep Python-specific security anti-patterns</td>
          </tr>
          <tr>
            <td className="tool-name">Gitleaks</td>
            <td>All files</td>
            <td>Secrets &amp; credentials committed to the repo</td>
          </tr>
          <tr>
            <td className="tool-name">Trivy</td>
            <td>All ecosystems + IaC</td>
            <td>Dependency CVEs, Dockerfile &amp; Terraform misconfig</td>
          </tr>
          <tr>
            <td className="tool-name">Hadolint</td>
            <td>Dockerfile</td>
            <td>Dockerfile best-practice &amp; security lint</td>
          </tr>
          <tr>
            <td className="tool-name">pip-audit</td>
            <td>Python (requirements, pyproject, Pipfile)</td>
            <td>Known CVEs in Python dependencies</td>
          </tr>
          <tr>
            <td className="tool-name">npm audit</td>
            <td>Node.js (package.json)</td>
            <td>Known CVEs in Node.js dependencies</td>
          </tr>
          <tr>
            <td className="tool-name">gosec</td>
            <td>Go</td>
            <td>Go-specific vulnerability patterns</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 id="trigger">Triggering a scan from CI</h2>
    <Code lang="bash" file=".github/workflows/security.yml"><Yaml>{`name: CyberCore SAST
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run CyberCore SAST
        run: |
          curl -X POST $CYBERCORE_URL/v1/sast/scan \\
            -H "Authorization: Bearer $CYBERCORE_TOKEN" \\
            -F repo_url=$GITHUB_SERVER_URL/$GITHUB_REPOSITORY \\
            -F ref=$GITHUB_SHA`}</Yaml></Code>

    <h2 id="failures">Failing the build</h2>
    <p>Pass <code>--fail-on critical,high</code> to make the action exit non-zero if the scan returns findings at or above a given severity. The pull request status check links straight to the finding in your dashboard.</p>

    <Callout kind="success" title="Findings are deduplicated across tools.">
      Trivy and pip-audit both flagging <code>CVE-2024-1234</code>? You see one finding
      with both attributions, not two near-identical entries.
    </Callout>
  </>
);

const DastService = () => (
  <>
    <p>Dynamic Application Security Testing — attacks your running application the same way a real attacker would. Underlying engine: <a href="https://www.zaproxy.org/" target="_blank" rel="noopener">OWASP ZAP</a>.</p>

    <h2 id="capabilities">Capabilities</h2>
    <div className="card-grid">
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">Crawling</div>
        <div className="card-title">Endpoint discovery</div>
        <div className="card-desc">Automatic discovery of routes, forms, and API surfaces.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">Injection</div>
        <div className="card-title">SQLi · CMDi · LDAPi</div>
        <div className="card-desc">Payload library tuned for low false-positive rates.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">XSS</div>
        <div className="card-title">Reflected · Stored · DOM</div>
        <div className="card-desc">Per-context payload selection with browser-based confirmation.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">Auth</div>
        <div className="card-title">Session &amp; cookie audit</div>
        <div className="card-desc">Broken auth, fixation, insecure cookie flags.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">IDOR</div>
        <div className="card-title">Cross-session probing</div>
        <div className="card-desc">Tests direct object references across authenticated sessions.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">SSRF</div>
        <div className="card-title">Outbound probing</div>
        <div className="card-desc">Detects server-side request-forgery vectors via a callback collaborator.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">Headers</div>
        <div className="card-title">CSP · HSTS · XFO</div>
        <div className="card-desc">Audits missing or misconfigured security headers.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">TLS</div>
        <div className="card-title">Cipher &amp; cert analysis</div>
        <div className="card-desc">Weak ciphers, expired certs, downgrade vulnerabilities.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">API</div>
        <div className="card-title">REST &amp; GraphQL fuzzing</div>
        <div className="card-desc">Malformed inputs, boundary conditions, type confusion.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">Rate limits</div>
        <div className="card-title">Bypass attempts</div>
        <div className="card-desc">Validates that your rate limiting actually works.</div>
      </div>
    </div>

    <h2 id="scope">Scope &amp; safeguards</h2>
    <Callout kind="danger" title="Only scan what you own.">
      DAST is offensive testing. You must own the target — or hold explicit written
      permission — before running a scan. CyberCore refuses out-of-scope targets by
      default; the safety check can only be disabled from a tenant-admin terminal.
    </Callout>

    <p>The service enforces scope at three layers:</p>
    <ol>
      <li><strong>Allowlist</strong> — only hostnames registered in your project are scannable.</li>
      <li><strong>Ownership challenge</strong> — for public hostnames, place a TXT record or <code>.well-known/cybercore</code> file.</li>
      <li><strong>Rate ceiling</strong> — request rate is capped to prevent accidental DoS of your own infrastructure.</li>
    </ol>

    <h2 id="launching">Launching a scan</h2>
    <Code lang="http" file="POST /v1/dast/scan"><Json>{`{
  "target": "https://staging.example.com",
  "scan_profile": "full",
  "auth": {
    "type": "form",
    "login_url": "https://staging.example.com/login",
    "username_field": "email",
    "password_field": "password",
    "credentials_secret": "ccs_xxxxxxxx"
  },
  "exclude": ["/admin/danger-zone"]
}`}</Json></Code>
  </>
);

const LogService = () => {
  const [tab, setTab] = useState("python");
  return (
    <>
      <p>Centralized log ingestion with project-based isolation. Drop the SDK in, get a unified view across every service your team runs.</p>

      <h2 id="how">How it works</h2>
      <ol>
        <li>Create a <strong>project</strong> in the dashboard.</li>
        <li>Generate an <strong>API key</strong> for that project (it's scoped — leaks don't span projects).</li>
        <li>Initialize <code>CyberLogCore</code> in your application with that key.</li>
        <li>Logs appear in your project, isolated from every other project on the instance.</li>
      </ol>

      <h2 id="sdk">SDK usage</h2>

      <div className="tabs">
        <button className={`tab ${tab==='python' ? 'active' : ''}`} onClick={()=>setTab('python')}>python</button>
        <button className={`tab ${tab==='js' ? 'active' : ''}`} onClick={()=>setTab('js')}>javascript</button>
        <button className={`tab ${tab==='go' ? 'active' : ''}`} onClick={()=>setTab('go')}>go</button>
      </div>

      {tab === "python" && (
        <Code lang="python" file="app.py"><Py>{`from cyberlog import CyberLogCore

log = CyberLogCore(api_key="ccl_your_key_here", project="my-backend")

log.info("User logged in", user_id="abc123")
log.error("Payment failed", order_id="xyz", amount=99.99)
log.warning("Rate limit approaching", endpoint="/api/v1/scan")`}</Py></Code>
      )}
      {tab === "js" && (
        <Code lang="javascript" file="app.js"><Js>{`import { CyberLogCore } from 'cyberlog';

const log = new CyberLogCore({
  apiKey: 'ccl_your_key_here',
  project: 'my-frontend',
});

log.info('Component mounted', { page: 'dashboard' });
log.error('API call failed', { status: 500, url: '/api/scans' });`}</Js></Code>
      )}
      {tab === "go" && (
        <Code lang="go" file="main.go"><Js>{`package main

import "github.com/omnisecura/cyberlog-go"

func main() {
  log, _ := cyberlog.New(cyberlog.Config{
    APIKey:  "ccl_your_key_here",
    Project: "my-service",
  })
  defer log.Close()

  log.Info("started", "version", "1.4.0")
  log.Error("db connection lost", "err", err)
}`}</Js></Code>
      )}

      <h2 id="features">Features</h2>
      <ul>
        <li><strong>Project isolation</strong> — each API key only sees its own logs.</li>
        <li>Structured logging with arbitrary metadata fields.</li>
        <li>Levels: <code>DEBUG</code>, <code>INFO</code>, <code>WARNING</code>, <code>ERROR</code>, <code>CRITICAL</code>.</li>
        <li>Full-text search across messages and metadata.</li>
        <li>Per-project retention policies.</li>
        <li>Webhook alerts on <code>ERROR</code> / <code>CRITICAL</code> events.</li>
      </ul>

      <h2 id="retention">Retention</h2>
      <p>Each project sets its own retention window — 7, 30, 90, 365 days, or unlimited. Storage backend is TimescaleDB with automatic compression after 7 days and tiered chunk migration on supported deployments.</p>

      <Callout kind="info" title="The SDK ships its own buffer.">
        Network blips don't drop logs. The Python and JS SDKs buffer up to 1,000 entries
        in memory and flush asynchronously with exponential-backoff retry. On clean
        shutdown the buffer is drained synchronously.
      </Callout>
    </>
  );
};

const AgentService = () => (
  <>
    <p>The <strong>CyberCore Agent</strong> runs on monitored machines and streams telemetry back to the platform. The agent-service ingests that stream, hands it to the ML anomaly worker, and produces actionable alerts.</p>

    <h2 id="collects">What the agent collects</h2>
    <ul>
      <li>Running processes and unusual process trees</li>
      <li>Network connections — open ports, suspicious outbound connections</li>
      <li>File system changes in sensitive directories</li>
      <li>CPU / RAM / disk anomalies (cryptomining, DoS)</li>
      <li>Failed login attempts and privilege-escalation events</li>
      <li>DNS queries (detecting C2 beaconing patterns)</li>
      <li>Loaded kernel modules</li>
    </ul>

    <h2 id="install">Installing the agent</h2>
    <Code lang="bash" file="terminal"><Sh>{`# Linux (systemd)
curl -fsSL https://get.cybercore.dev/agent.sh | sudo bash -s -- \\
  --enroll-token=cct_xxxxxxxx \\
  --server=https://cybercore.mycompany.internal

systemctl status cybercore-agent`}</Sh></Code>

    <h2 id="platforms">Supported platforms</h2>
    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Platform</th><th>Status</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td>Linux x86_64 (glibc ≥ 2.31)</td><td><span className="sev" data-level="low">stable</span></td><td>Tested on Debian 11+, Ubuntu 22.04+, RHEL 8+</td></tr>
          <tr><td>Linux aarch64</td><td><span className="sev" data-level="low">stable</span></td><td>Raspberry Pi 4/5, AWS Graviton</td></tr>
          <tr><td>macOS (Apple Silicon &amp; Intel)</td><td><span className="sev" data-level="medium">beta</span></td><td>Requires Full Disk Access permission</td></tr>
          <tr><td>Windows</td><td><span className="sev" data-level="info">planned</span></td><td>On the roadmap — see <a onClick={()=>window.__nav('roadmap')}>roadmap</a></td></tr>
        </tbody>
      </table>
    </div>

    <h2 id="anomaly">Anomaly detection</h2>
    <p>Telemetry is streamed through <code>ml-worker</code>, which builds a per-host baseline over the first 7 days and scores deviations afterwards. The baseline is continuous — known deployments, scheduled jobs, and seasonal traffic patterns are absorbed.</p>

    <Callout kind="warn" title="Agent updates aren't auto by default.">
      Self-updating agents are on the roadmap. For now, treat agent upgrades like any
      other host package — schedule them, test them on staging fleets first, and watch
      the alert volume settle.
    </Callout>
  </>
);

const AlertService = () => (
  <>
    <p>One layer for every notification the platform produces. Dedup, escalation, channels — configured once, applied to all event types.</p>

    <h2 id="channels">Channels</h2>
    <ul>
      <li>Email (SMTP)</li>
      <li>Webhook (signed with HMAC-SHA256)</li>
      <li>Slack &amp; Discord</li>
      <li>Telegram</li>
      <li>PagerDuty <span style={{color:"var(--mute)", fontSize:12}}>(planned)</span></li>
    </ul>

    <h2 id="rules">Routing rules</h2>
    <p>Rules combine a <strong>predicate</strong> (severity, source, project, tags) with a <strong>destination</strong> (one or more channels). Order matters — the first matching rule wins unless it's marked <code>continue</code>.</p>

    <Code lang="yaml" file="alert-rules.yaml"><Yaml>{`rules:
  - name: critical-prod-everything
    when:
      severity: [CRITICAL]
      tags: [env:production]
    notify:
      - slack: "#sec-incidents"
      - pagerduty: ops
    continue: false

  - name: scan-findings-to-eng
    when:
      source: [sast-service, dast-service]
      severity: [HIGH, MEDIUM]
    notify:
      - slack: "#engineering-security"`}</Yaml></Code>

    <h2 id="dedup">Deduplication &amp; escalation</h2>
    <ul>
      <li><strong>Dedup window</strong> — identical alerts collapse into a counted occurrence within a configurable window (default 1 hour).</li>
      <li><strong>Escalation</strong> — if not acknowledged in N minutes, the next contact in the chain is notified.</li>
      <li><strong>Snooze</strong> — silence known-noisy alert classes per-project for a fixed duration.</li>
    </ul>

    <Callout kind="info" title="You will not get 200 emails.">
      The alert-service is paranoid about volume. Even at the worst end of a misconfigured
      scan, the practical ceiling is one digest per dedup window per channel.
    </Callout>
  </>
);

const Sdks = () => (
  <>
    <p>Thin client libraries that ship logs (and soon, metrics) to your CyberCore instance.</p>

    <div className="card-grid">
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">cyberlog-python</div>
        <div className="card-title">Python SDK</div>
        <div className="card-desc"><code>pip install cyberlog</code> — Python 3.9+, sync &amp; async clients, optional <code>logging</code> handler.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">cyberlog-js</div>
        <div className="card-title">JavaScript SDK</div>
        <div className="card-desc"><code>npm install cyberlog</code> — Node 18+ and browser builds, ESM/CJS dual-package.</div>
      </div>
      <div className="card" style={{cursor:"default"}}>
        <div className="card-eyebrow">cyberlog-go</div>
        <div className="card-title">Go SDK</div>
        <div className="card-desc"><code>go get github.com/omnisecura/cyberlog-go</code> — zero-dep, context-aware.</div>
      </div>
    </div>

    <h2 id="common">Common patterns</h2>
    <ul>
      <li>Drop-in adapter for the language's stdlib logger (<code>logging</code>, <code>console</code>, <code>log/slog</code>).</li>
      <li>Background flush thread / goroutine — no synchronous HTTP on the hot path.</li>
      <li>Context propagation — request ID, user ID, trace ID attached automatically when provided.</li>
      <li>Graceful shutdown — buffer drains on SIGTERM with a configurable timeout.</li>
    </ul>

    <Callout kind="info" title="More SDKs welcome.">
      The wire protocol is HTTPS + JSON lines with optional gzip. Rust, Ruby and Elixir
      clients are community-driven — see <a onClick={()=>window.__nav('contributing')}>Contributing</a>.
    </Callout>
  </>
);

const Configuration = () => (
  <>
    <p>All configuration is environment variables. Copy <code>.env.example</code>, fill in secrets, restart.</p>

    <h2 id="required">Required</h2>
    <Code lang="bash" file=".env"><Sh>{`# Required
POSTGRES_PASSWORD=change_me_in_production
JWT_SECRET=change_me_in_production_use_64_char_random_string
ENVIRONMENT=development`}</Sh></Code>

    <h2 id="optional">Optional</h2>
    <Code lang="bash" file=".env (continued)"><Sh>{`# OAuth (Google sign-in)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Notifications
SMTP_HOST=
SMTP_PORT=587
SLACK_WEBHOOK_URL=

# Storage tuning
POSTGRES_MAX_CONNECTIONS=200
TIMESCALE_RETENTION_DAYS=90
REDIS_MAXMEMORY=2gb`}</Sh></Code>

    <h2 id="secrets">Generating secrets</h2>
    <Code lang="bash" file="terminal"><Sh>{`# 64-char JWT secret
openssl rand -base64 48

# Postgres password
openssl rand -base64 24`}</Sh></Code>

    <Callout kind="danger" title="Rotate JWT_SECRET carefully.">
      Changing <code>JWT_SECRET</code> invalidates every active session immediately. Plan
      rotations during low-traffic windows and brief your users — or expose the secondary
      key feature (coming in v0.5) to dual-sign during a grace period.
    </Callout>
  </>
);

const Deployment = () => (
  <>
    <h2 id="local">Local development</h2>
    <p>Docker Compose with profile-based selective startup — see <a onClick={()=>window.__nav('quick-start')}>Quick start</a>.</p>

    <h2 id="kubernetes">Kubernetes (production)</h2>
    <p>Helm charts live in <code>k8s/</code>. Tested on k3s — ideal for a home server or a single-node VPS.</p>

    <Code lang="bash" file="terminal"><Sh>{`helm install cybercore ./k8s/cybercore \\
  --namespace cybercore \\
  --create-namespace \\
  -f values.production.yaml`}</Sh></Code>

    <h2 id="infra">Recommended infrastructure</h2>
    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Tier</th><th>Setup</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><strong>Dev / staging</strong></td><td>k3s on a Hetzner VPS (~€35/mo)</td><td>Single node, 8 vCPU / 16 GB</td></tr>
          <tr><td><strong>Production</strong></td><td>AWS EKS or Hetzner Cloud + managed LB</td><td>3-node minimum, dedicated DB</td></tr>
          <tr><td><strong>Air-gapped</strong></td><td>On-prem k3s + mirrored registry</td><td>Bundle published as a sealed tarball</td></tr>
        </tbody>
      </table>
    </div>

    <Callout kind="info" title="GDPR &amp; data residency.">
      For European users, host inside the EU — Hetzner (DE/FI), Scaleway (FR), or your
      own DC. CyberCore stores no telemetry off-instance, so residency is whatever you
      pick.
    </Callout>

    <h2 id="observability">Observability</h2>
    <p>The Helm chart bundles Prometheus, Grafana, Loki and Jaeger. Dashboards for every service are provisioned automatically; alerts are wired into the same alert-service pipeline your users see.</p>
  </>
);

const Roadmap = () => (
  <>
    <p>What's coming, roughly in order. Dates are intent, not commitment.</p>

    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Quarter</th><th>Item</th><th>Status</th></tr></thead>
        <tbody>
          <tr><td>2026 Q2</td><td>SAST support for C# (Roslyn analyzers)</td><td><span className="sev" data-level="medium">in progress</span></td></tr>
          <tr><td>2026 Q2</td><td>DAST authenticated scan flows</td><td><span className="sev" data-level="medium">in progress</span></td></tr>
          <tr><td>2026 Q3</td><td>Windows agent</td><td><span className="sev" data-level="info">planned</span></td></tr>
          <tr><td>2026 Q3</td><td>ML-based code vuln detection (beyond rule-based)</td><td><span className="sev" data-level="info">planned</span></td></tr>
          <tr><td>2026 Q3</td><td>Compliance reports (OWASP Top 10, CWE/SANS 25)</td><td><span className="sev" data-level="info">planned</span></td></tr>
          <tr><td>2026 Q4</td><td>Integrations: Jira, GitHub Issues, PagerDuty</td><td><span className="sev" data-level="info">planned</span></td></tr>
          <tr><td>2026 Q4</td><td>Mobile app for alert management</td><td><span className="sev" data-level="info">planned</span></td></tr>
          <tr><td>2027 Q1</td><td>Self-updating agent via agent-service</td><td><span className="sev" data-level="info">planned</span></td></tr>
        </tbody>
      </table>
    </div>

    <Callout kind="info" title="Voting on priorities.">
      Each roadmap item is tracked as a GitHub issue with a <code>roadmap</code> label.
      Reactions on those issues feed into the next planning round — that's the most
      direct way to push something up the queue.
    </Callout>
  </>
);

const Contributing = () => (
  <>
    <p>CyberCore is in active development. Contributions are welcome.</p>

    <h2 id="workflow">Workflow</h2>
    <ol>
      <li>Fork the repository.</li>
      <li>Create a feature branch: <code>git checkout -b feat/your-feature</code>.</li>
      <li>Commit with conventional commits: <code>feat(sast): add PHP scanning support</code>.</li>
      <li>Open a pull request against <code>main</code>.</li>
    </ol>

    <h2 id="review">Review process</h2>
    <p>All PRs require one maintainer approval. Security-touching changes — anything in <code>auth-service</code>, <code>scan-service</code>, the agent, or affecting how credentials flow — require <strong>two</strong> approvals, and one must be from a maintainer with the <code>security</code> tag.</p>

    <h2 id="security-report">Reporting a vulnerability</h2>
    <Callout kind="danger" title="Don't open a public issue.">
      Report it privately to <code>security@cybercore.dev</code>. We aim to respond within
      48 hours and will credit responsible disclosure in the changelog.
    </Callout>

    <h2 id="license">License</h2>
    <p>CyberCore is MIT-licensed. You are free to use, modify, and distribute it, including for commercial purposes. The CyberCore name and logo are separate trademarks.</p>
  </>
);

const TenantService = () => (
  <>
    <p>Tenants are the top-level boundary in CyberCore. One CyberCore instance can serve many isolated tenants — each with its own users, projects, scan history, and alert rules.</p>

    <h2 id="model">Data model</h2>
    <ul>
      <li><strong>Tenant</strong> — a billing/ownership boundary. One per company in most deployments.</li>
      <li><strong>Organization</strong> — a logical grouping inside a tenant (e.g. <em>Platform</em>, <em>Mobile</em>, <em>Data</em>).</li>
      <li><strong>Project</strong> — a unit of scope: a repo, a service, an environment. Findings and logs attach here.</li>
      <li><strong>User</strong> — belongs to one or more tenants with per-tenant roles.</li>
    </ul>

    <h2 id="roles">Roles</h2>
    <div className="tbl-wrap">
      <table className="tbl">
        <thead><tr><th>Role</th><th>Can</th><th>Cannot</th></tr></thead>
        <tbody>
          <tr><td><code>owner</code></td><td>Everything, incl. billing &amp; deletion</td><td>—</td></tr>
          <tr><td><code>admin</code></td><td>Manage users, projects, scan policy</td><td>Delete the tenant, change ownership</td></tr>
          <tr><td><code>member</code></td><td>View findings, trigger scans, ack alerts</td><td>Manage users or rotate keys</td></tr>
          <tr><td><code>viewer</code></td><td>Read-only access to dashboards</td><td>Trigger any write action</td></tr>
        </tbody>
      </table>
    </div>

    <Callout kind="info" title="MFA enforcement is tenant-scoped.">
      Setting <code>require_mfa: true</code> on a tenant forces every member to enroll on
      next login. New invites can't complete signup without enrolling.
    </Callout>
  </>
);

/* ---------- registry ---------- */

window.PAGES = [
  // Getting started
  { id: "welcome",      group: "Introduction",  title: "Welcome",            lede: "Open-source platform for cybersecurity monitoring, vulnerability scanning, and threat detection — yours to host.", icon: SideIcons.home,   body: Welcome,       toc: ["Project status","Start here","What you get out of the box"] },
  { id: "quick-start",  group: "Introduction",  title: "Quick start",        lede: "Boot the core CyberCore stack with Docker Compose in five minutes.",            icon: SideIcons.rocket, body: QuickStart,    toc: ["Prerequisites","1. Clone & configure","2. Pick a profile","3. Run it","4. First login"] },
  { id: "architecture", group: "Introduction",  title: "Architecture",       lede: "How services, workers, agents and the dashboard fit together.",                  icon: SideIcons.arch,   body: Architecture,  toc: ["Data flow","Component independence"] },

  // Services
  { id: "auth-service",         group: "Services", title: "Auth service",          lede: "Identity, MFA, OAuth2 — the front door to the platform.",                  icon: SideIcons.shield, body: AuthService,    toc: ["Registration","Multi-factor authentication","OAuth2 / social login","Sessions & tokens","Brute-force protection"] },
  { id: "tenant-service",       group: "Services", title: "Tenants & organizations", lede: "Multi-tenant boundaries, projects, and role-based access.",            icon: SideIcons.agent,  body: TenantService, toc: ["Data model","Roles"], pillNew: false },
  { id: "scan-service",         group: "Services", title: "Scan service",          lede: "Unified scan orchestrator — every finding, one shape.",                      icon: SideIcons.scan,   body: ScanService,    toc: ["Unified finding format","Example finding (rendered)","Severity normalization","Deduplication"] },
  { id: "sast-service",         group: "Services", title: "SAST service",          lede: "Static analysis — eight tools, automatic language detection, deduplicated.", icon: SideIcons.sast,   body: SastService,    toc: ["Input methods","Tools shipped","Triggering a scan from CI","Failing the build"] },
  { id: "dast-service",         group: "Services", title: "DAST service",          lede: "Dynamic application testing on top of OWASP ZAP.",                            icon: SideIcons.dast,   body: DastService,    toc: ["Capabilities","Scope & safeguards","Launching a scan"] },
  { id: "log-service",          group: "Services", title: "Log service",           lede: "Project-isolated log ingestion with Python, JS, and Go SDKs.",                icon: SideIcons.log,    body: LogService,     toc: ["How it works","SDK usage","Features","Retention"] },
  { id: "agent-service",        group: "Services", title: "Agent service",         lede: "Host telemetry and anomaly detection for your fleet.",                       icon: SideIcons.agent,  body: AgentService,   toc: ["What the agent collects","Installing the agent","Supported platforms","Anomaly detection"] },
  { id: "alert-service",        group: "Services", title: "Alert service",         lede: "Unified notifications — dedup, escalation, every channel.",                  icon: SideIcons.alert,  body: AlertService,   toc: ["Channels","Routing rules","Deduplication & escalation"] },

  // SDKs
  { id: "sdks", group: "SDKs", title: "Client SDKs", lede: "Thin libraries for Python, JavaScript and Go.", icon: SideIcons.sdk, body: Sdks, toc: ["Common patterns"] },

  // Operating
  { id: "configuration", group: "Operating", title: "Configuration", lede: "Environment variables — required and optional.", icon: SideIcons.cog,    body: Configuration, toc: ["Required","Optional","Generating secrets"] },
  { id: "deployment",    group: "Operating", title: "Deployment",    lede: "Local Docker, Kubernetes via Helm, air-gapped bundles.", icon: SideIcons.deploy, body: Deployment, toc: ["Local development","Kubernetes (production)","Recommended infrastructure","Observability"] },

  // Community
  { id: "roadmap",      group: "Project", title: "Roadmap",      lede: "What's planned — and what's already underway.",       icon: SideIcons.map,    body: Roadmap,      toc: [], pillNew: true },
  { id: "contributing", group: "Project", title: "Contributing", lede: "How to send a pull request and report security issues.", icon: SideIcons.heart, body: Contributing, toc: ["Workflow","Review process","Reporting a vulnerability","License"] },
];

window.GROUPS = ["Introduction", "Services", "SDKs", "Operating", "Project"];
