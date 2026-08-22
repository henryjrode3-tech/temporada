# MVP scope

What ships in this build, what deliberately does not, and how to tell the
difference.

---

## The demo business

**Mike's Plumbing**, San Rafael, California. Fictional.

| | |
| --- | --- |
| Services | Emergency plumbing · Water heater repair · Drain cleaning · Leak repair · Toilet repair · Faucet repair · Sewer/drain · General plumbing |
| Hours | Mon–Fri 8:00–18:00 · Sat 9:00–14:00 · Sun closed |
| Service area | San Rafael and surrounding Marin County |

---

## In scope

### The core loop
Missed call → automatic SMS → customer replies → agent qualifies → offers real
slots → customer picks → appointment created in the database → lead becomes
`BOOKED` → dashboard and timeline update.

### Agent
- Identifies service type and urgency from natural language
- Collects description, address, preferred time
- Confirms the business actually serves the request
- Offers only slots that are genuinely free
- Escalates on uncertainty, on emergencies, and on repeated failure
- Returns schema-validated structured output; invalid output retries once, then escalates

### Owner control
**Take Over** halts the agent immediately. The owner types directly to the
customer. **Return to AI** restores it. Enforced server-side.

### Dashboard
Today's Leads · Missed Calls · Recovered Leads · Appointments Booked ·
Estimated Revenue Recovered · AI Conversations — **all computed from database
state**, none hardcoded.

### Pages
Landing · Dashboard · Leads · Conversations · Appointments · AI Agent ·
Business Settings · Activity

### Demo controls
- **Simulate Missed Call** — name, phone, problem, optional scenario
- **Six one-click scenarios** (below)
- **Simulate Follow-Up** — fires the follow-up immediately instead of waiting

### Six scenarios
| # | Scenario | What it demonstrates |
| --- | --- | --- |
| 1 | Water heater leak | Standard qualification and booking |
| 2 | Clogged drain | Routine, lower urgency, different value |
| 3 | Emergency (burst pipe / gas) | Safety interception and escalation |
| 4 | Customer goes quiet | Follow-up behaviour |
| 5 | Question the agent can't answer | Honest "I don't know" + human review |
| 6 | Requested slot unavailable | Re-offer without inventing availability |

---

## Out of scope for this build

Deliberate omissions, listed so nobody mistakes them for oversights.

| Not built | Why |
| --- | --- |
| Real Twilio / Google Calendar / hosted LLM | Requires paid credentials. Interfaces and mocks are in place; adding a real provider is one file. |
| Authentication / multi-tenancy | Single demo business. The schema is multi-tenant (`businessId` throughout) but there is no login. |
| Real telephony | No carrier integration. Missed calls are simulated. |
| Payments, invoicing, dispatch, routing | Not part of the recovery loop. |
| Background job scheduler | Follow-ups fire on demand via the button rather than on a timer. |

---

## How to judge whether it works

Not "does it look finished" but:

1. Every dashboard number changes when you create a lead. No hardcoded metrics.
2. The agent asks *different* questions depending on what it already knows. It
   is not replaying a script.
3. The word "booked" appears only after a row exists in `Appointment`.
4. Taking over stops the agent — provably, from the server, not just visually.
5. Asking for an unavailable slot produces a genuine alternative, not a
   fabricated confirmation.
6. Describing a gas leak produces safety guidance and escalation, not a booking
   flow.

---

## Honest limitations

- **Estimated values are assumptions**, labelled as such everywhere. Water heater
  $700, drain cleaning $350, emergency $1,200, general $400. They are not revenue.
- **The mock agent is deterministic.** It is a real policy engine, not a language
  model, so it is predictable and cheap but less fluent than a hosted model.
  Swapping in Anthropic or OpenAI changes the prose, not the control flow.
- **Follow-ups are manual** in the demo.
- **Demo mode is enforced.** Nothing can text a real phone number without an
  explicit real provider *and* `DEMO_MODE=false`.
