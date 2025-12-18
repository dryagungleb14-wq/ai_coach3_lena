# Sentinel's Journal

## 2025-05-22 - FastAPI Swagger UI & CSP
**Vulnerability:** N/A (Constraint discovery)
**Learning:** Adding a strict `Content-Security-Policy` (e.g., `default-src 'self'`) to a FastAPI backend breaks the auto-generated Swagger UI (`/docs`). FastAPI's default docs lookups load CSS/JS assets from public CDNs (e.g., jsdelivr.net), which are blocked by strict CSPs.
**Prevention:** When implementing CSP for FastAPI, either explicitly allow the required CDNs (unsafe-inline might also be needed for some versions) or configure FastAPI to serve static assets locally. For this task, CSP was omitted to preserve functionality.
