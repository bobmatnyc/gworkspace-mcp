# ADR-001: Do Not Integrate googleworkspace/cli (gws) as Backend

**Date:** 2026-03-06
**Status:** Decided
**Decision:** Leave current direct REST architecture as-is

---

## Context

On 2026-03-02, Google released `@googleworkspace/cli` (`gws`) — a Rust-based CLI distributed
via npm that dynamically registers Google Workspace API commands via the Discovery Service and
can run as an MCP daemon (`gws mcp`).

We investigated two integration models:

1. **gcloud CLI** — Infeasible. gcloud is a GCP infrastructure tool with zero coverage for
   Gmail, Calendar, Docs, Sheets, Slides, or Tasks. Auth model (ADC/service accounts) is
   incompatible with per-user OAuth.

2. **googleworkspace/cli (gws)** — Partially viable but not worth the delta (see below).

---

## Decision

Do not integrate `gws`. Retain the current architecture: direct REST calls via
`httpx.AsyncClient` with per-user OAuth 2.0 tokens.

---

## Reasoning

### What gws does well

- Runs as a persistent MCP daemon (not per-call subprocess — no spawn overhead)
- Dynamically registers commands from Google Discovery API — broad basic CRUD surface
- Agent-friendly setup flow (browser-wielding agent can automate `gws auth setup`)
- Well-implemented for v0.x; endorsed by Guillermo Rauch (Vercel CEO) at launch

### Why the delta is not worth it

**Coverage gap (~65-75% of our tools have no gws equivalent):**
- Rich Docs formatting (format_text, apply_heading_style, set_margins, create_list, insert_table)
- Document tabs (5 tools), Mermaid diagram rendering
- Sheets formatting (format_cells, set_number_format, merge_cells, set_column_width) and charts
- Slides layouts, text boxes, images, formatted content (most of 21 tools)
- Batch Gmail operations (batch_archive, batch_trash, batch_modify, batch_mark_read)
- Gmail vacation responder, filters
- Drive multipart binary upload/download

**Stability risk:**
- Pre-v1.0; breaking changes are explicit and frequent (v0.7.0 already removed
  domain-wide delegation support)
- Not an officially supported Google product

**Auth complexity:**
- Would require token injection via `GOOGLE_WORKSPACE_CLI_TOKEN` env var per invocation,
  duplicating refresh logic we already handle natively

**Current architecture is already optimal:**
- Async-native via httpx (no blocking, full concurrency for MCP multi-tool calls)
- `google-api-python-client` was already removed (unused — see commit 609612b)
- Only `google-auth` and `google-auth-oauthlib` needed at runtime

---

## Future Consideration

Revisit at `gws` v1.0 (estimated 6-12 months). At that point `gws mcp` could serve as
a lightweight alternative deployment for users who only need basic CRUD and want zero
Python setup. It would complement rather than replace this server.
