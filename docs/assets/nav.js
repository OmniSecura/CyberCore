/**
 * CyberCore Docs — Shared navigation injector.
 *
 * Include this script at the bottom of every page's <body>.
 * It injects the sidebar nav, marks the active link, and wires
 * the hamburger button for mobile.
 *
 * To add a new page:
 *  1. Add it to NAV_ITEMS below (section + label + href).
 *  2. Copy _template.html and fill in the content.
 *  Done — nav updates everywhere automatically.
 */

const NAV_ITEMS = [
  {
    section: "Overview",
    items: [
      { label: "Introduction",    href: "index.html" },
      { label: "Architecture",    href: "architecture.html" },
      { label: "Getting Started", href: "getting-started.html" },
    ]
  },
  {
    section: "Services",
    items: [
      { label: "Auth Service",          href: "service-auth.html" },
      { label: "Organization Service",  href: "service-organizations.html" },
      { label: "Scan Service",          href: "service-scan.html" },
    ]
  },
  {
    section: "API Reference",
    items: [
      { label: "Auth API",          href: "api-auth.html" },
      { label: "Organizations API", href: "api-organizations.html" },
      { label: "Scans API",         href: "api-scans.html" },
    ]
  },
  {
    section: "Infrastructure",
    items: [
      { label: "Docker & Deployment", href: "deployment-docker.html" },
      { label: "SAST Worker",         href: "workers-sast.html" },
      { label: "Database Schema",     href: "database-schema.html" },
    ]
  },
  {
    section: "Other",
    items: [
      { label: "Security Model", href: "security.html" },
      { label: "Contributing",   href: "contributing.html" },
    ]
  },
];

(function () {
  // ── Build sidebar HTML ─────────────────────────────────────────
  const currentPage = location.pathname.split("/").pop() || "index.html";

  let html = "";
  for (const group of NAV_ITEMS) {
    html += `<div class="sidebar-section">
      <div class="sidebar-label">${group.section}</div>`;
    for (const item of group.items) {
      const active = item.href === currentPage ? " active" : "";
      html += `<a class="sidebar-link${active}" href="${item.href}">${item.label}</a>`;
    }
    html += `</div>`;
  }

  const container = document.getElementById("nav-container");
  if (container) container.innerHTML = html;

  // ── Hamburger toggle ────────────────────────────────────────────
  const hamburger = document.getElementById("hamburger");
  const sidebar   = document.querySelector(".sidebar");

  if (hamburger && sidebar) {
    hamburger.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });

    // Close sidebar when a link is clicked on mobile
    sidebar.querySelectorAll(".sidebar-link").forEach(link => {
      link.addEventListener("click", () => sidebar.classList.remove("open"));
    });

    // Close sidebar when clicking outside
    document.addEventListener("click", (e) => {
      if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ── Collapsible endpoint cards ──────────────────────────────────
  document.querySelectorAll(".endpoint-header").forEach(header => {
    header.addEventListener("click", () => {
      header.closest(".endpoint").classList.toggle("open");
    });
  });

  // ── Auto-open endpoint if URL has matching hash ─────────────────
  if (location.hash) {
    const target = document.querySelector(location.hash);
    if (target && target.classList.contains("endpoint")) {
      target.classList.add("open");
      setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    }
  }
})();
