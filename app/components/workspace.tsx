"use client";

import Link from "next/link";
import { useState } from "react";
import { logout } from "@/server/auth/actions";

export function Workspace({ children }: { children: React.ReactNode }) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  return (
    <div className={`app-shell${sidebarExpanded ? "" : " sidebar-collapsed"}`}>
      <header className="topbar">
        <div className="topbar-brand">
          <button
            className="sidebar-toggle"
            type="button"
            aria-controls="workspace-sidebar"
            aria-expanded={sidebarExpanded}
            aria-label={sidebarExpanded ? "Collapse menu" : "Expand menu"}
            title={sidebarExpanded ? "Collapse menu" : "Expand menu"}
            onClick={() => setSidebarExpanded(expanded => !expanded)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <strong>Invoice<span>Flow</span></strong>
        </div>
        <form action={logout}>
          <button className="sign-out" type="submit">Sign out</button>
        </form>
      </header>
      <aside className="sidebar" id="workspace-sidebar" hidden={!sidebarExpanded}>
        <p>WORKSPACE</p>
        <Link className="active" aria-current="page" href="/">
          Dashboard
        </Link>
      </aside>
      {children}
    </div>
  );
}
