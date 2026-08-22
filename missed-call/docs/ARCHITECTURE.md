# Architecture

An AI missed-call recovery system for local plumbing businesses. When a call
goes unanswered, the system texts the caller, an agent conducts the follow-up
conversation, qualifies the lead, and books an appointment — with the owner able
to seize control of any conversation at any moment.

This project is **completely standalone**. It shares no code, dependencies, or
database with anything else in this repository.

---

## 1. The one non-negotiable rule

**Free-form model text never controls application state.**

The agent returns a validated envelope. The `message` field is the only part
that reaches the customer; every state change flows through `leadUpdate` and
`action`, both schema-checked before anything is written:

```ts
{
  message: string,                  // shown to the customer
  leadUpdate: { serviceType?, description?, urgency?, address?, preferredTime? },
  action: "NONE" | "REQUEST_APPOINTMENT" | "ESCALATE_HUMAN",
  confidence: number
}
```

If the envelope fails validation, the turn is retried once. If it fails again
the conversation escalates to human review. It never guesses.

The corollary matters just as much: **an appointment is "booked" only after the
database says so.** The agent may *request* a slot; it cannot confirm one. The
booking path checks live availability, writes the row, and only then does the
customer hear the word "booked". Any other ordering means eventually telling
someone their plumber is coming when nobody is.

---

## 2. Component map

```
                    ┌──────────────────────────────┐
                    │  Next.js App Router (UI)     │
                    │  Dashboard · Leads · Convos  │
                    │  Appointments · Agent · …    │
                    └──────────────┬───────────────┘
                                   │  server actions / route handlers
                    ┌──────────────▼───────────────┐
                    │  lib/services/               │
                    │  missedCall · conversation   │
                    │  booking · followup · metrics│
                    └──────────────┬───────────────┘
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
     │  lib/agent/     │  │  lib/providers/ │  │   lib/events    │
     │  policy · state │  │  AI · SMS · Cal │  │   audit trail   │
     │  safety · schema│  │  (mock + real)  │  └─────────────────┘
     └─────────────────┘  └─────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  Prisma → PostgreSQL         │
                    │  own database: `missedcall`  │
                    └──────────────────────────────┘
```

`lib/agent/` is pure: given a conversation and a business config it returns an
envelope. No database, no network, no clock reads that aren't injected. That is
what makes the agent's behaviour testable without mocking the world.

---

## 3. Provider abstractions

Three interfaces, each with a working mock and room for a real implementation.
The application depends only on the interface.

| Interface | Mock | Real (later) |
| --- | --- | --- |
| `AIProvider` | Deterministic policy agent | Anthropic / OpenAI |
| `SMSProvider` | Records to DB, delivers in-app | Twilio |
| `CalendarProvider` | Slots in DB | Google Calendar |

Selection is by environment variable, defaulting to mocks:

```
AI_PROVIDER=mock | anthropic
SMS_PROVIDER=mock | twilio
CALENDAR_PROVIDER=mock | google
```

**Demo mode is the default and is enforced, not merely displayed.** The SMS
provider refuses to transmit externally unless a real provider is explicitly
configured *and* `DEMO_MODE=false`. A misconfiguration cannot text a real
person by accident — the failure mode of a system like this is somebody's
actual customer receiving a robot message, so the safe state is the default.

### The mock AI is a real agent, not a script

`MockAIProvider` runs an actual policy: it extracts service type and urgency
from the customer's words, tracks which required fields are still missing, asks
for the most valuable one next, checks live availability before offering times,
and escalates when confidence is low. It handles the six demo scenarios by
*reasoning over state*, not by matching them. Swapping in a hosted model
replaces the language, not the control flow — the same envelope, the same
validation, the same guard rails.

---

## 4. Conversation control

A conversation is in exactly one of three modes:

| Mode | Who replies | How it changes |
| --- | --- | --- |
| `AI` | agent | default |
| `HUMAN` | owner | owner clicks **Take Over**, or agent escalates |
| `PAUSED` | nobody | agent globally paused in settings |

The mode is checked *inside* the message-handling service, not in the UI. A
stale browser tab cannot cause the agent to answer over the owner: the server
decides. When the owner takes over, the agent stops immediately and stays
stopped until control is returned.

---

## 5. Safety

Encoded in `lib/agent/safety.ts` and applied before any message is emitted.

**Hard prohibitions.** No invented prices, no guaranteed outcomes, no invented
availability, no claiming a booking that does not exist, no repair instructions
for dangerous work, no unsupported diagnosis, and no claiming to be human when
asked directly.

**Emergency interception** runs *before* normal handling. Gas smells, sparking
electrics, sewage backups and uncontrolled flooding produce an immediate safety
response — leave, call 911 or the gas utility, shut off the main — and escalate
to a human. The agent does not try to troubleshoot a possible gas leak, and it
does not put a booking flow in front of someone standing in a flooding house.

**Uncertainty has a scripted exit:** *"I'm not certain about that. I'll have
Mike's Plumbing follow up with you."* — and the lead moves to `HUMAN_REVIEW`.

---

## 6. Data model

Nine models. The relationships that carry the design:

- `Lead` is the unit of work; `Conversation` is the channel; they are 1:1 but
  separate because a lead can outlive its conversation.
- `Message` records `sender` as `CUSTOMER | AI | HUMAN | SYSTEM`, so the
  transcript shows exactly who said what — including which replies were the
  owner's rather than the agent's.
- `Event` is an append-only audit trail. Every state change writes one. This is
  what makes the Activity timeline truthful rather than reconstructed.
- `BusinessSettings` and `AgentSettings` are read by the agent on every turn, so
  editing them in the UI changes behaviour on the next message — not on restart.

Estimated values are stored per service type and always rendered as
**"estimated value"**. They are a modelling aid for the ROI view, not revenue,
and the UI never says otherwise.

---

## 7. Testing

Unit tests cover the pure pieces: urgency classification, envelope validation,
service extraction, availability, revenue arithmetic, safety interception.

The test that matters is the integration one, which drives the full path
against a real database:

```
missed call → SMS sent → customer reply → AI response → qualification
            → appointment requested → slot checked → booked → metrics updated
```

If that passes, the product works. Everything else is detail.
