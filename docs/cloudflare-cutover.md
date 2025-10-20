# Cloudflare Cutover Runbook

Finalise the Cloudflare migration once the GridBoss domains have been delegated to Cloudflare. This checklist assumes DNS records were previously hosted elsewhere and all services (frontend on Vercel, API/worker on Render, optional CDN on CloudFront) are already running.

## 1. Prerequisites
- Cloudflare zone created for `grid-boss.com` with nameservers applied at the registrar.
- Vercel project configured for the frontend (`app.grid-boss.com`).
- Render Web Service (`api.grid-boss.com`) provisioned and healthy.
- Optional CloudFront distribution ready if a CDN is required for static assets (e.g. `cdn.grid-boss.com`).
- Sentry DSN (if enabled) and `/readyz` health checks already validated in the deployment environment.

## 2. DNS Records
Create the following records inside the Cloudflare dashboard (DNS tab):

| Name | Type | Value | Proxy Status |
| ---- | ---- | ----- | ------------ |
| `app` | `CNAME` | `<vercel-app-target>` | Proxied |
| `api` | `CNAME` | `<render-service-target>` | **DNS only** (orange cloud off) |
| `_vercel` | `TXT` | Value from the Vercel domain verification screen | Proxied (defaults to DNS-only and is fine) |
| `cdn` (optional) | `CNAME` | `<cloudfront-distribution-domain>` | Proxied |
| `@` | `A` | `192.0.2.1` | Proxied |
| `www` | `CNAME` | `app.grid-boss.com` | Proxied |

> The apex `A` record uses a placeholder IP (Cloudflare “dummy” address) in order to activate redirect rules; Cloudflare will serve the redirect responses.

DNS propagation: confirm the records with `nslookup app.grid-boss.com` and `nslookup api.grid-boss.com` from multiple locations once saved.

## 3. SSL/TLS Configuration
In the Cloudflare **SSL/TLS > Overview** tab:

- Set **SSL/TLS mode** to **Full** (not Flexible).
- Enable **Always Use HTTPS**.
- Enable **HSTS** (optional but recommended once certificates are confirmed).
- In **Edge Certificates**, ensure “TLS 1.0/1.1” are disabled and TLS 1.2+ is enforced.

These ensure the API and frontend remain accessible over HTTPS only, while Cloudflare re-encrypts traffic to Vercel and Render.

## 4. Page Rules & Redirects
Under **Rules > Redirect Rules** (or Page Rules if still in use):

1. Redirect apex to the application:
   - Expression: `(http.host eq "grid-boss.com")`
   - Action: Dynamic redirect to `https://app.grid-boss.com${uri.path}` with status 301

2. Redirect `www` to the application (optional if handled in Vercel):
   - Expression: `(http.host eq "www.grid-boss.com")`
   - Action: Dynamic redirect to `https://app.grid-boss.com${uri.path}` status 301

Under **Rules > Cache Rules** create a bypass for the API:

- Expression: `(http.host eq "api.grid-boss.com")`
- Cache action: **Bypass cache**
- Origin cache control: **Respect origin** (default)

This prevents Cloudflare from caching API responses, while allowing the frontend/CDN endpoints to benefit from caching.

## 5. Firewall & Security
- Leave the API (`api.grid-boss.com`) unproxied to avoid websocket/WebSocket handshake issues and to keep Render’s IP visible for debugging. All other records can remain proxied.
- Optionally create a basic WAF rule blocking common bot user agents on the frontend if abuse becomes an issue.
- Verify that rate limiting (either Cloudflare or application-level) is enabled according to the security plan.

## 6. Verification Checklist
Run through the following curl checks after DNS propagates:

```powershell
curl -I https://grid-boss.com           # expect 301 -> https://app.grid-boss.com
curl -I https://www.grid-boss.com       # expect 301 -> https://app.grid-boss.com
curl -I https://app.grid-boss.com       # expect 200 from Vercel
curl -I https://api.grid-boss.com/readyz  # expect 200 and Sentry check status `ok` when DSN configured
curl -I https://api.grid-boss.com/healthz # expect 200 response
```

Additional steps:

- Visit the frontend via `https://app.grid-boss.com` and confirm assets load without mixed-content warnings.
- Trigger an API request through the frontend to verify CORS headers remain correct.
- Check Render’s logs after the cutover to ensure requests are flowing through Cloudflare IP ranges.
- If Sentry is enabled, intentionally hit a non-existent API endpoint and confirm the error appears in Sentry (Cloudflare should not block the outbound traffic).

## 7. Post-Cutover Monitoring
- Enable Cloudflare analytics (traffic, cache, firewall) to watch for spikes or blocked requests.
- Keep an eye on Render and Vercel dashboards for any unusual latency or 5xx increases.
- Review certificate expiration dates in Cloudflare and issue tailored reminders (Cloudflare auto-renews, but upstream origin certificates must also be valid).

## 8. Rollback Guidance
If a critical issue is discovered:

1. Pause Cloudflare proxying (toggle the orange cloud to grey) for affected records to route traffic directly to Vercel/Render.
2. Revert DNS at the registrar to the previous nameservers if necessary.
3. Re-run the verification checks and monitor dashboards once the issue is resolved.

Document the findings in the runbook and update this guide with any new caveats for future cutovers.
