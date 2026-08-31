# Landing app operations

Covers `landing/` (Next.js), specifically the public, unauthenticated
`POST /api/early-access` endpoint used to capture early-access sign-ups.

## Application-level controls (enforced in code, in this repo)

`landing/src/app/api/early-access/route.ts` and `landing/src/lib/early-access.ts`:

- Body size cap: requests over **16 KiB** are rejected with **HTTP 413**
  before the body is even `JSON.parse`'d.
- Strict field validation (Zod schema in `landing/src/lib/early-access.ts`),
  rejecting anything outside these bounds with **HTTP 400**:
  - `fullName`: 2–120 chars
  - `email`: valid email, max 254 chars
  - `phone`: 8–32 chars
  - `company`: 2–160 chars
  - `role`, `teamSize`, `priorityInterest`: max 80 chars each (optional)
  - `note`: max 2,000 chars (optional)
- All user-supplied values are HTML-escaped (`escapeHtml` in
  `landing/src/lib/early-access.ts`, escaping `&`, `<`, `>`, `"`, `'`) before
  interpolation into either generated email body (`landing/src/lib/resend.ts`),
  closing the stored/reflected XSS-into-email-client hole that existed when
  values were interpolated raw. `mailto:`/`tel:` link targets are additionally
  run through `encodeURIComponent`.
- Truthful response codes: the route only returns `200 { success: true }`
  after a **real** user-confirmation email has actually been sent via Resend.
  - If Resend is not configured (dev/staging without `RESEND_API_KEY`), the
    route returns `200 { success: true, simulated: true }` and explicitly
    states no email was sent — it never claims delivery that didn't happen.
  - If Resend **is** configured but the real user-confirmation email fails to
    send, the route returns **HTTP 502**, not a false 200.

## Edge/WAF controls (NOT enforced by this repo — must be configured on the hosting platform before launch)

The checked-in `Caddyfile` does **not** proxy the landing route, so it cannot
and does not enforce any of the following. These limits must be configured
directly on whatever platform fronts `landing/` (its WAF / edge rate-limit
product) before the early-access form is exposed publicly:

- **Rate limit:** at most **5 requests per IP per 10 minutes** to
  `POST /api/early-access`; the 6th request in that window must receive
  **HTTP 429**.
- **Body size cap at the edge:** reject bodies over **16 KiB** at the edge as
  defense in depth, in addition to the application-level 413 check above.
- **Optional bot challenge:** if the hosting platform's bot-management
  product is available, add a browser challenge rule above **3 requests per
  minute per IP**. This is a separate, probabilistic control — verify its
  expected status code/interaction independently; it is not covered by (and
  should not be conflated with) the deterministic 429 rate-limit test above.

Do not claim in code, comments, or docs that this repo enforces the per-IP
rate limit — it doesn't, and can't, from application code alone provide real
abuse resistance (a single app instance behind a load balancer cannot see
per-IP request counts across all instances without an external store). The
16 KiB body-size check is enforced in application code (see above); the rate
limit is edge-only.

## Lead storage (explicit non-decision — do not silently start one)

This slice does **not** add a lead database. Registrations are only ever
relayed via the two Resend emails (user confirmation + optional admin
notification). Before launch, product/legal must explicitly choose one of:

- (a) an approved, durable, privacy-governed lead store with a documented
  retention/deletion policy, or
- (b) outbound email as the documented system of record (current state).

Do not add ad hoc persistence for leads without that decision being made and
documented here.
