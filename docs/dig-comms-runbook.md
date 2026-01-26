# DIG Ops Communications Runbook (Announcements + Newsletter + Segments)

**Purpose:** Create one operational pipeline for DIG communications—**announcements**, **newsletter**, and **segmented outreach**—that is consistent, auditable, and easy to run weekly.

**Outcome:** DIG can ship communications reliably without list chaos, with clear approvals, accessibility baked in, and measurable results.

---

## 0) Operating Model

### Channels in scope
- **Email** (primary): announcements + newsletter
- **Web archive**: public-facing archive of sent communications (recommended)
- **Optional add-ons**: SMS, social, Teams/Slack posts (later)

### Content types
- **Announcement**: time-sensitive, single topic, short
- **Newsletter**: multi-item digest (monthly or biweekly)
- **Segmented outreach**: targeted message to a subgroup (members only, region, federal employees, sponsors, etc.)

### Non-negotiables
- **Accessibility**: plain language, headings, descriptive links, alt text, captions where applicable
- **Governance**: approvals and change log
- **List hygiene**: opt-in/opt-out and suppression respected

---

## 1) Data & Systems (Minimal + Durable)

### System of record (recommended)
- **Salesforce** for Contacts, Membership status, segments, communication history (or a lightweight CRM if not)
- **Email service** (MailerSend, Mailgun, SendGrid, etc.) for delivery + analytics
- **WordPress** (or Astro) for public archive posts (optional but powerful)

### Minimum data needed on each Contact
- Email
- Membership Status (Active/Lapsed/Non-member)
- Segment Tags (picklist/multi-select):
  - Federal / Non-federal
  - Region / Chapter
  - Member / Non-member
  - Sponsor contact
  - Event attendee
- Communication Preferences:
  - Newsletter opt-in (Y/N)
  - Announcements opt-in (Y/N)
  - Sponsor outreach opt-in (Y/N)
- Suppression flags:
  - Do not email (Y/N)
  - Bounced / Unsubscribed (tracked by ESP)

---

## 2) List Governance (So It Doesn’t Become a Mess)

### 2.1 Source-of-truth rule
- **Salesforce is the source of truth** for who is eligible for what.
- Email service lists are **synced outputs**, not the canonical database.

### 2.2 Standard segments (start here)
- **All members (Active)**
- **All contacts (opt-in)**
- **Federal members**
- **Non-federal members**
- **Sponsors & prospects**
- **Event attendees (last 90 days)**
- **Lapsed members (last 12 months)**

### 2.3 Suppression rule
Always suppress:
- Unsubscribed
- Hard bounces
- Do not email
- Invalid emails

---

## 3) Templates & Brand (Day-1 Must Have)

### 3.1 Email templates (minimum set)
1. **Announcement** (single-card, clear CTA)
2. **Newsletter** (multi-section with table of contents)
3. **Event reminder**
4. **Event follow-up / recap**
5. **Sponsor update** (for sponsor communications)
6. **Membership nudge** (renewal / join)

### 3.2 Accessibility template rules
- Use real headings (H2/H3) where supported
- Short paragraphs
- Link text describes destination (“Register for DIG Town Hall” not “Click here”)
- Alt text on images
- Avoid image-only flyers; include text equivalent
- Video: captioned; provide transcript when practical

---

## 4) The Communications Pipeline (DIG Ops Weekly Cadence)

### 4.1 Intake (content collection)
Create a single intake method:
- Email alias: `comms@...` OR a form
- Required fields:
  - Message type (announcement/newsletter item)
  - Target audience (segment)
  - Desired send date/time
  - Call to action link
  - Owner (who provided content)
  - Accessibility needs (ASL video? captions? interpreters? etc.)

### 4.2 Editorial triage (15 minutes)
- Confirm audience + goal
- Confirm timing
- Confirm owner and approvals
- Assign priority:
  - P0 urgent (today/tomorrow)
  - P1 normal (this week)
  - P2 backlog (next newsletter)

### 4.3 Drafting (AI-assisted if desired)
- Convert raw bullets into:
  - Subject line options (3)
  - Preview text options (2)
  - Body with clear CTA
  - One-sentence summary for archive

### 4.4 Approval (bureaucrat-proof)
**Two-step approval model**
- **Content approval** (policy/accuracy): owner or designated approver
- **Send approval** (ops): DIG Ops checks list + links + accessibility + formatting

> Keep approvals lightweight: timestamp, approver name, version number.

### 4.5 Send + archive
- Send through ESP
- Create archive entry:
  - WordPress post OR Salesforce record OR static archive page
  - Include subject, send date, and the body content (or a web version link)

---

## 5) Newsletter Operating Procedure (Monthly or Biweekly)

### 5.1 Newsletter structure (recommended)
1. Header + mission line
2. **Top story**
3. **Events** (upcoming)
4. **Policy / advocacy updates**
5. **Member spotlight**
6. **Sponsor thanks** (if applicable)
7. Footer: preferences + unsubscribe + contact

### 5.2 Timeline (example: monthly)
- **Week -2:** Collect items
- **Week -1:** Draft + first approval
- **Week 0:** Final proof + send
- **Week +1:** Review metrics + archive highlight

### 5.3 Quality checks (pre-send)
- Links tested
- Dates/timezones verified (ET by default)
- Accessibility review
- Segment verified + suppression verified
- Preview in mobile/desktop

---

## 6) Announcements Operating Procedure (Fast Lane)

### 6.1 When to use announcements
- Event registration open
- Urgent policy update
- Time-sensitive call-to-action
- Critical community notice

### 6.2 Standard announcement format
- One sentence: what is it
- Two bullets: why it matters
- Clear CTA button/link
- Contact for questions
- Optional: short ASL video (captioned) with text equivalent

---

## 7) Metrics (Board-Friendly, Not Vanity)

Track per send:
- Delivered
- Open rate (directional; don’t obsess)
- Click-through rate (most important)
- Unsubscribe rate
- Bounce rate
- Segment size

Track monthly:
- List growth
- Member vs non-member engagement
- Top-performing CTAs
- Best send times (by segment)

---

## 8) Automations (High-Impact, Low Drama)

### 8.1 Segment sync (Salesforce → ESP)
- Nightly sync:
  - Active members list
  - Federal members list
  - Sponsors list
  - Suppression list

### 8.2 “One button” newsletter production (optional)
- A workflow that:
  - pulls approved items
  - composes the newsletter template
  - creates a draft campaign in the ESP

### 8.3 Event lifecycle automations (comms-adjacent)
- Registration confirmation email
- Reminder 7 days / 1 day
- Post-event recap + survey

---

## 9) Roles & Responsibilities (Lean Team Version)

- **Comms Lead (content)**: editorial voice, decides what ships
- **DIG Ops (operations)**: list integrity, scheduling, approvals, archive
- **Accessibility reviewer (optional)**: quick check for accessibility compliance
- **Requester/Owner**: provides source material and approves accuracy

---

## 10) Verification Checklist (Go-Live)

- [ ] Contacts have opt-in/out fields and suppression flags
- [ ] Standard segments defined and testable
- [ ] ESP lists map to segments correctly
- [ ] Announcement + Newsletter templates exist
- [ ] Approval process documented (even if lightweight)
- [ ] Archive process works (web version or internal archive)
- [ ] First test send to internal list completed successfully
- [ ] Metrics dashboard/report exists (basic is fine)

---

## 11) Change Log

- Date:
- Changed by:
- Systems touched:
  - [ ] Salesforce
  - [ ] Email service
  - [ ] WordPress/Astro archive
- Notes / exceptions:

