# Rename “Sales” → “DIG Ops” Runbook

**Goal:** Replace the *display label* “Sales” with **“DIG Ops”** across your ecosystem (website, Salesforce, M365/Power Automate, docs) **without breaking** APIs, automations, or standard Salesforce constructs.

---

## 0) Scope Rules (Bureaucrat‑Proof)

### Change (safe: labels/text)
- Navigation labels, page titles, headings
- Internal team/category labels
- Folder/report/dashboard titles
- Permission set **labels**, queue/group **names**
- Power Automate flow **names**, SharePoint view/column **display names**

### Do NOT change unless explicitly intended (risky: references)
- Salesforce **API names / DeveloperName** fields
- Standard Salesforce app/object concepts (“Sales” app, Leads, Opportunities) unless you are rebranding the operating model
- Anything that would affect integrations (fields, IDs, endpoint paths)

**Rule of thumb:** Rename **labels first**; leave **API/developer names** unchanged.

---

## 1) Global Sweep (Repos + Docs)

### 1.1 Safe search terms
- Exact word: `\bSales\b`
- Phrases:
  - `Sales Ops` → `DIG Ops`
  - `Sales Operations` → `DIG Ops`
  - `Sales team` → `DIG Ops team`
  - `Sales Queue` → `DIG Ops Queue`
  - `Sales KPI` → `DIG Ops KPI`

### 1.2 Guardrail
- Do **not** replace inside **“Salesforce”**.
- Avoid broad replacements like `Sal` or case-insensitive patterns.

### 1.3 Recommended workflow
1. Search: `\bSales\b`
2. Replace in batches:
   - Docs/Markdown first
   - UI strings next
   - Config last
3. Re-run search and confirm remaining hits are intentional.

---

## 2) Website (WordPress + Astro)

### 2.1 WordPress
- Menus: rename “Sales” → “DIG Ops”
- Page titles: update visible title to “DIG Ops”
- URLs/slugs:
  - Prefer **keeping existing slugs** for stability (e.g., `/sales/`)
  - If you create `/dig-ops/`, add redirects from old paths

### 2.2 Astro (14ten site)
- Navigation labels
- Page headings and section headers
- Metadata:
  - OpenGraph title/description
  - SEO title/description if present

**Verification:** Search built output or source for `\bSales\b`.

---

## 3) Salesforce (Label‑First, Safe Order)

### 3.1 Lightning App naming
**If you created a custom app currently labeled “Sales”:**
- Setup → **App Manager** → (your app) → **Edit**
  - **App Name (Label):** `DIG Ops`
  - Leave **Developer Name** unchanged

**If users are using the standard Salesforce “Sales” app and you want “DIG Ops” instead:**
- Create a **new custom Lightning App** called **DIG Ops**
- Add the relevant tabs/objects
- Assign app access via Profiles/Permission Sets
- (Optional) remove access to standard Sales app for most users

### 3.2 Permission Sets / Permission Set Groups
- Rename **labels**:
  - `Sales - …` → `DIG Ops - …`
  - `Sales Team` → `DIG Ops Team`
- Leave **API names** unchanged.

### 3.3 Queues / Public Groups / Roles
- Queues: `Sales Queue` → `DIG Ops Queue`
- Public Groups: `Sales` → `DIG Ops`
- Roles/titles: only if it’s purely branding (avoid changing role hierarchy structure).

### 3.4 Reports / Dashboards / Folders
- Folder names
- Dashboard titles
- Report titles and chart labels

### 3.5 Flows / Automation
- Rename **Flow labels** and descriptions:
  - “Sales Intake” → “DIG Ops Intake”
- Leave Flow **API Name** unchanged.

---

## 4) M365 / SharePoint / Power Automate

### 4.1 SharePoint
- List display names (where applicable)
- View names: “Sales” → “DIG Ops”
- Column display names:
  - `Sales Status` → `DIG Ops Status`
  - `Sales Owner` → `DIG Ops Owner`

### 4.2 Power Automate
- Flow names: `Sales - …` → `DIG Ops - …`
- Email subjects/templates: update visible labels only

### 4.3 Teams / Channels (optional)
- Channel name: `Sales` → `DIG Ops`
- Update pinned tabs/links if they contain “Sales”.

---

## 5) Regression Prevention

### 5.1 Naming Standard
- Canonical team label: **DIG Ops**
- Adjective form: **DIG Ops** (not “DIG Operational”)
- Use consistently in:
  - Titles
  - Navigation
  - Headings
  - Templates

### 5.2 Repo guardrail (optional)
- Add a lightweight check (manual or CI) to flag new occurrences of `\bSales\b` in UI strings.

---

## 6) Final Verification Checklist

- [ ] All navigation/menu items show **DIG Ops**
- [ ] Page headers/titles show **DIG Ops**
- [ ] Salesforce app label shows **DIG Ops** (or DIG Ops app exists and assigned)
- [ ] Permission set **labels** updated
- [ ] Queues/groups renamed where relevant
- [ ] Reports/dashboards/folders renamed
- [ ] Flow **labels** renamed (not API names)
- [ ] No accidental replacement inside **Salesforce**
- [ ] Search for `\bSales\b` returns only intentionally kept items

---

## 7) Change Log (fill in)

- Date:
- Changed by:
- Systems touched:
  - [ ] WordPress
  - [ ] Astro
  - [ ] Salesforce
  - [ ] SharePoint
  - [ ] Power Automate
  - [ ] Docs/Repos
- Notes / exceptions:

