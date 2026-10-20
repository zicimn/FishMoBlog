---
name: nav-redesign-direction
description: User wants sidebar menus converted to top/horizontal navigation bars (structural, not restyle) in the Fish Platform UI
metadata:
  type: feedback
---

When asked to redesign a "menu bar / 菜单栏" into a "navigation bar / 导航栏", the user wants a structural conversion to a top horizontal nav bar, not a restyle of the vertical sidebar.

Applied 2026-07-31:
- `src/App.vue` — fixed left sidebar (250px, collapsible) replaced by a single-row glass top navbar (brand icon + nav links + search + dark toggle + profile/logout + mobile hamburger drawer). KEPT.
- `src/views/UserHome.vue` — the profile page's vertical sidebar menu was initially converted to a horizontal segmented nav bar, but the user asked to revert it ("将个人主页界面改为上一版本"). The profile page should KEEP its original left sidebar (avatar + vertical menu, two-column layout).

**Why:** The explicit request was to redesign the sidebar menu as a navigation bar — a top/horizontal nav (导航栏) is the intended target for the main app shell. But the user prefers the personal profile page's original left-sidebar layout and reverted that change.

**How to apply:** For future header/nav redesigns, prefer single-row glass navbars (rgba(255,255,255,0.7) + blur(24px), border rgba(226,232,240,0.5)), pill active states with an accent underline micro-interaction, generous spacing, and a mobile hamburger drawer that reuses the existing `isCollapsed`/`toggleSidebar` logic (do not touch `<script setup>` blocks for visual changes). Keep the global `.glass-card` class intact — views depend on it. Do NOT convert UserHome's left sidebar menu to a horizontal nav without explicit request; the user reverted exactly that.
