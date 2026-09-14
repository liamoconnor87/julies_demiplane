# Front-End Reliability & UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the CDN/init-order fragility behind the "modifier stuck at 0" tester feedback, and fix the four UX bugs Liam listed in `misc/todos.txt`.

**Architecture:** No new dependencies or build tooling. Two tasks hardening the existing vanilla-JS/HTMX front end (vendor two CDN scripts, isolate bind-step failures); four tasks are small, independent edits (one CSS, one JS constant, one template reorder, one JS rebind fix). Each task stands alone and can ship in any order.

**Tech Stack:** Flask + Jinja2 + HTMX + vanilla JS (`static/scripts/dnd_sheet.js`), Bootstrap 5.3.3, Flask-Talisman for CSP.

**Spec:** This plan's spec is the conversation itself: the front-end-reliability diagnosis given to Liam (dependency-loading theory for the tester's bug report) plus the four items in `misc/todos.txt` as of this date. No separate spec doc exists.

## Global Constraints

- No new dependencies (stdlib/native/already-installed only — see `ponytail` in the session config).
- This repo has no automated test suite for the Flask app (only an unrelated `admin/test_postgres_to_sqlite.py`). Per `CLAUDE.md`'s "use your judgement on whether a test is worth it" and Liam's own preference for manual testing over ad-hoc scripts, every task below ends in a **manual verification** step in a real browser, not a written test.
- **Never run git commands that write state** (`add`, `commit`, `branch`, `push`, etc.) — Liam handles all of that himself. Tasks below end with "leave the change uncommitted for review," not a commit step.
- Match existing code style: 4-space indent, semicolons, `dataset.xBound === 'true'` guards for idempotent re-binding (already the pattern throughout `dnd_sheet.js` — reuse it, don't invent a new one).

---

## File Structure

| File | Change |
|---|---|
| `static/scripts/vendor/htmx-1.9.12.min.js` (new) | Vendored copy of htmx, currently pulled from `unpkg.com` |
| `static/scripts/vendor/bootstrap-5.3.3.bundle.min.js` (new) | Vendored copy of Bootstrap's JS bundle, currently pulled from `cdn.jsdelivr.net` |
| `templates/index.html` | Point the two `<script>` tags at the vendored files instead of CDN URLs |
| `templates/admin.html` | Same, for its htmx `<script>` tag |
| `app.py` | Drop `cdn.jsdelivr.net` / `unpkg.com` from the Talisman CSP's `script-src` now that no script loads from either |
| `static/scripts/dnd_sheet.js` | Add a `safeBind()` wrapper around every call in `initializeUiBindings()` and the `load` listener; bump the feat/inventory autosave debounce; add the missing rebind calls to the `custom-buffs-section-container` branch of the `htmx:afterSwap` handler |
| `static/css/auth.css` | Swap the two non-themeable `var(--primary-color-transparent)` uses for `var(--field-bg-colour)` |
| `templates/components/feats/feat_row.html` | Move the rune-divider `<div>` above the description field |

---

### Task 1: Vendor htmx and Bootstrap's JS bundle instead of loading them from CDN

**Why this is the fix for the tester's bug:** the ability-score modifier is computed entirely client-side, in `recomputeAbilityRowDisplay()` ([dnd_sheet.js:2352-2386](static/scripts/dnd_sheet.js#L2352-L2386)), wired up by `bindAbilityAutoSave()` when `initializeUiBindings()` runs on page load ([dnd_sheet.js:735-768](static/scripts/dnd_sheet.js#L735-L768)). The only way for a stat edit to never move the modifier is for `dnd_sheet.js` to never finish initializing. Two CDN scripts sit ahead of it in `<head>`/`<body>` — `unpkg.com/htmx.org@1.9.12` (no pinned file path, redirects, no SRI) and `cdn.jsdelivr.net`'s Bootstrap bundle — and the page's CSP ([app.py:89-93](app.py#L89-L93)) only allows scripts from those two hosts plus `'self'`. Any network condition that blocks or mis-serves either host (corporate proxy, ad blocker, regional block, a bad SRI match) removes a whole class of failure the tester likely hit. Vendoring both files removes the CDN as a runtime dependency entirely.

**Files:**
- Create: `static/scripts/vendor/htmx-1.9.12.min.js`
- Create: `static/scripts/vendor/bootstrap-5.3.3.bundle.min.js`
- Modify: `templates/index.html:298-302`
- Modify: `templates/admin.html:10`
- Modify: `app.py:89-93`

**Interfaces:** None — this task doesn't change any function signature other tasks rely on. It only changes where two `<script src>` tags point.

- [x] **Step 1: Download the exact pinned versions already referenced in the templates**

```bash
mkdir -p static/scripts/vendor
curl -fSL https://cdn.jsdelivr.net/npm/htmx.org@1.9.12/dist/htmx.min.js \
    -o static/scripts/vendor/htmx-1.9.12.min.js
curl -fSL https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js \
    -o static/scripts/vendor/bootstrap-5.3.3.bundle.min.js
```

- [x] **Step 2: Verify the Bootstrap download against the SRI hash already in `index.html`**

`index.html:299` already pins Bootstrap's bundle to `sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz`. Confirm the downloaded file matches before trusting it:

```bash
openssl dgst -sha384 -binary static/scripts/vendor/bootstrap-5.3.3.bundle.min.js | openssl base64 -A
```

Expected: `YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz` (matches the `sha384-` value already in the template). If it doesn't match, stop and re-download — don't vendor an unverified file.

- [x] **Step 3: Point `templates/index.html` at the vendored files**

Replace [index.html:298-302](templates/index.html#L298-L302):

```html
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
crossorigin="anonymous"></script>
<script src="https://unpkg.com/htmx.org@1.9.12"></script>
<script src="{{ url_for('static', filename='scripts/dnd_sheet.js') }}?v={{ static_version }}"></script>
```

with:

```html
<script src="{{ url_for('static', filename='scripts/vendor/bootstrap-5.3.3.bundle.min.js') }}"></script>
<script src="{{ url_for('static', filename='scripts/vendor/htmx-1.9.12.min.js') }}"></script>
<script src="{{ url_for('static', filename='scripts/dnd_sheet.js') }}?v={{ static_version }}"></script>
```

(No `integrity`/`crossorigin` needed any more — the browser now trusts these the same way it trusts `dnd_sheet.js`, because they're same-origin.)

- [x] **Step 4: Point `templates/admin.html` at the vendored htmx copy**

Replace [admin.html:10](templates/admin.html#L10):

```html
<script src="https://unpkg.com/htmx.org@1.9.12"></script>
```

with:

```html
<script src="{{ url_for('static', filename='scripts/vendor/htmx-1.9.12.min.js') }}"></script>
```

- [x] **Step 5: Narrow the CSP now that nothing loads scripts from either CDN host**

In [app.py:89-93](app.py#L89-L93):

```python
    'script-src': [
        "'self'",
        'https://cdn.jsdelivr.net',
        'https://unpkg.com',
    ],
```

becomes:

```python
    'script-src': [
        "'self'",
    ],
```

Leave `style-src` and `font-src` alone — Google Fonts, Bootstrap Icons and Font Awesome's CSS still load from `cdn.jsdelivr.net`/`fonts.googleapis.com`/`fonts.gstatic.com`, and none of those affect the bug being fixed here.

- [ ] **Step 6: Manual verification**

1. Start the app locally (`docker logs` per `CLAUDE.md`'s Debugging section, or however you normally run it) and open the character sheet in a browser.
2. Open DevTools → Network, reload, and confirm `bootstrap-5.3.3.bundle.min.js` and `htmx-1.9.12.min.js` load with status 200 from your own origin (not `cdn.jsdelivr.net`/`unpkg.com`) — filter the Network tab by "vendor" to see them.
3. Open DevTools → Console and confirm there are no CSP violation errors and no uncaught exceptions on load.
4. Type a new value into any ability score box and confirm the modifier next to it updates immediately (this is the bug the tester reported — confirm it still works with everything self-hosted).
5. Open a Bootstrap-driven control (the account dropdown in the top-right) and confirm it still opens/closes — this exercises the vendored Bootstrap JS specifically.
6. Load `/admin` as an admin user and confirm the page still works (htmx-driven table actions), to check the `admin.html` change.

- [x] **Step 7: Leave uncommitted for review** — this repo's convention is that Liam stages and commits changes himself; do not run `git add`/`git commit`.

---

### Task 2: Isolate bind-step failures so one throwing function can't silently break the rest of the page

**Why:** `initializeUiBindings()` ([dnd_sheet.js:735-768](static/scripts/dnd_sheet.js#L735-L768)) runs ~26 bind functions back-to-back with no error isolation, and the `load` listener ([dnd_sheet.js:1-6](static/scripts/dnd_sheet.js#L1-L6)) does the same for 4 more before it. If any one of them throws — a bad DOM assumption, a future edit that references something not yet in the page — every function called *after* it in that same list never runs. `bindAbilityAutoSave()` is roughly 20 calls into that list, so this is a second, independent way the tester's exact symptom could happen, and it'll keep being a risk for every future addition to this list until it's isolated.

**Files:**
- Modify: `static/scripts/dnd_sheet.js` (add one helper function; touch every call site inside the `load` listener and `initializeUiBindings()`)

**Interfaces:**
- Produces: `safeBind(fn)` — takes a zero-argument function, calls it, and on a thrown error logs it via `console.error` and continues. Nothing outside this task calls it directly, but Task 6 should route any *new* bind call it adds through it too, for consistency.

- [x] **Step 1: Add the helper next to the other shared helpers**

Add just above `function initializeUiBindings()` ([dnd_sheet.js:735](static/scripts/dnd_sheet.js#L735)):

```javascript
// One throwing bind step must not take down every bind step after it in the
// same sequential list (initializeUiBindings, the `load` listener). Each
// step is independent UI wiring, so isolate failures and keep going.
function safeBind(fn) {
    try {
        fn();
    } catch (err) {
        console.error(`[dnd_sheet] ${fn.name || 'bind step'} failed:`, err);
    }
}
```

- [x] **Step 2: Wrap every call in `initializeUiBindings()`**

Change every line in the body of `initializeUiBindings()` from `bindFoo();` to `safeBind(bindFoo);` (function reference, not a call — no parens inside `safeBind(...)`). There are 26 calls in that function as of this plan; wrap all of them the same way, e.g.:

```javascript
function initializeUiBindings() {
    safeBind(bindAddClassButton);
    safeBind(bindAddStatButton);
    safeBind(selectFeatField);
    // ...continue for every existing call in the function, unchanged order...
    safeBind(bindHitDiceSteppers);
}
```

- [x] **Step 3: Wrap the 4 direct calls in the `load` listener**

[dnd_sheet.js:1-6](static/scripts/dnd_sheet.js#L1-L6):

```javascript
window.addEventListener("load", () => {
    initializeUiBindings();
    bindDeleteCharacterDropdown();
    bindSubBarTabs();
    bindThemePanel();
```

becomes:

```javascript
window.addEventListener("load", () => {
    safeBind(initializeUiBindings);
    safeBind(bindDeleteCharacterDropdown);
    safeBind(bindSubBarTabs);
    safeBind(bindThemePanel);
```

- [ ] **Step 4: Manual verification**

1. Temporarily add `throw new Error('test')` as the first line of some early bind function (e.g. `bindAddClassButton`), reload the page, and confirm in the console you see the `[dnd_sheet] bindAddClassButton failed:` log — but the ability modifier still updates live when you edit a stat, proving later bind steps still ran. Remove the temporary throw afterward.
2. With the throw removed, click around the sheet as normal (add a feat, toggle a tracker, open the theme panel) and confirm nothing regressed — this step should be invisible in the non-error case.

- [x] **Step 5: Leave uncommitted for review.**

---

### Task 3: Fix stale (non-themeable) background colour on the login/signup dropdown

**Root cause:** `misc/todos.txt` line 1 says the login/signup "info bar" and the Login/Sign Up buttons use "stale" background colours not connected to the theme, unlike the logged-in dropdown. Grepping for the actual colour values shows why: every themeable colour in `auth.css` reads a CSS variable that the theme system controls (`--field-bg-colour`, `--label-colour`, `--secondary-color-dark`, all populated per-user by [theme_vars_oob.html](templates/components/ui/theme_vars_oob.html) and the inline `<style id="user-theme-vars">` block in [index.html:66-83](templates/index.html#L66-L83)). Two spots, both only in the logged-out half of the dropdown, instead use `var(--primary-color-transparent)` — a fixed value (`rgba(184, 168, 205, 0.85)`, [dnd_sheet.css:3](static/css/dnd_sheet.css#L3)) that has no corresponding field in `THEME_DEFAULTS`/`UserTheme.COLOUR_FIELDS` and can never change no matter what the user picks in the theme panel:

- [auth.css:44-51](static/css/auth.css#L44-L51) — the "Sign up to save your character" info alert background.
- [auth.css:132-137](static/css/auth.css#L132-L137) — the Login/Sign Up submit button's `:hover` background.

The logged-in half of the same dropdown (greeting, logout button, admin button) never references `--primary-color-transparent` anywhere, which is exactly why it "just works."

**Files:**
- Modify: `static/css/auth.css:47` and `static/css/auth.css:136`

**Interfaces:** None — pure CSS, no JS/template contract changes.

- [x] **Step 1: Swap both occurrences**

At [auth.css:44-51](static/css/auth.css#L44-L51):

```css
.auth-dropdown-body .alert.alert-success {
    background: var(--primary-color-transparent);
    border: 1px solid var(--secondary-color-dark);
    color: var(--label-colour);
    border-radius: 0;
}
```

becomes:

```css
.auth-dropdown-body .alert.alert-success {
    background: var(--field-bg-colour);
    border: 1px solid var(--secondary-color-dark);
    color: var(--label-colour);
    border-radius: 0;
}
```

At [auth.css:132-137](static/css/auth.css#L132-L137):

```css
.auth-btn-primary:hover {
    background: var(--primary-color-transparent);
    color: var(--label-colour);
    border-color: var(--label-colour);
    opacity: 1;
}
```

becomes:

```css
.auth-btn-primary:hover {
    background: var(--field-bg-colour);
    color: var(--label-colour);
    border-color: var(--label-colour);
    opacity: 1;
}
```

`--field-bg-colour` is what every other surface in this dropdown already uses (the toggle button, the menu, the tabs, the inputs), so this makes the logged-out half consistent with the logged-in half instead of introducing another new themeable field.

- [ ] **Step 2: Manual verification**

1. Log in, open the theme panel, and pick a `field_bg_colour` that's visually distinct from the current one (e.g. a bright colour). Save it.
2. Log out (or open a private window to view as a guest) and open the Login/Sign Up dropdown.
3. Confirm the "Sign up to save your character" info banner's background now matches the new field background colour instead of the fixed lavender.
4. Hover the "Login" and "Sign Up" submit buttons and confirm their hover background also matches the new colour instead of flashing the fixed lavender.
5. Log back in and confirm the logged-in dropdown (unaffected by this change) still looks correct.

- [x] **Step 3: Leave uncommitted for review.**

---

### Task 4: Slow down the feat/inventory name & description autosave debounce

**Root cause:** `misc/todos.txt` line 3 says typing in the feat/trait and inventory name/description fields is disrupted by how quickly the field saves. `featAutoSave` and `inventoryAutoSave` ([dnd_sheet.js:879](static/scripts/dnd_sheet.js#L879) and [dnd_sheet.js:1961](static/scripts/dnd_sheet.js#L1961)) both use the shared 1500ms default from `createDebouncedSaver()`. When it fires, `saveFeatRow()`/`saveInventoryRow()` swap the row's entire `outerHTML` with a freshly server-rendered copy ([dnd_sheet.js:898-906](static/scripts/dnd_sheet.js#L898-L906)) — a brand-new DOM node, which drops focus/cursor position. A 1.5s pause between words (common while composing a description) is enough to trigger that swap mid-thought.

Fix exactly what's asked — a longer wait — without touching the shared constant, since abilities also use it (`abilityAutoSave`, [dnd_sheet.js:2398](static/scripts/dnd_sheet.js#L2398)) and nobody has reported that being too fast.

**Files:**
- Modify: `static/scripts/dnd_sheet.js:879` and `static/scripts/dnd_sheet.js:1961`

**Interfaces:** None — `createDebouncedSaver(delayMs)` already takes an explicit override; this task just passes one in two more places.

- [x] **Step 1: Add a named constant and use it for both savers**

Near the existing `AUTO_SAVE_DEBOUNCE_MS` ([dnd_sheet.js:337](static/scripts/dnd_sheet.js#L337)):

```javascript
const AUTO_SAVE_DEBOUNCE_MS = 1500;
// Card-item text fields (feat/trait and inventory name+description) swap
// the whole row's outerHTML on save, which drops focus/cursor position —
// give typing pauses more room before that happens.
const CARD_ITEM_AUTO_SAVE_DEBOUNCE_MS = 3000;
```

Then at [dnd_sheet.js:879](static/scripts/dnd_sheet.js#L879):

```javascript
const featAutoSave = createDebouncedSaver();
```

becomes:

```javascript
const featAutoSave = createDebouncedSaver(CARD_ITEM_AUTO_SAVE_DEBOUNCE_MS);
```

And at [dnd_sheet.js:1961](static/scripts/dnd_sheet.js#L1961):

```javascript
const inventoryAutoSave = createDebouncedSaver();
```

becomes:

```javascript
const inventoryAutoSave = createDebouncedSaver(CARD_ITEM_AUTO_SAVE_DEBOUNCE_MS);
```

- [ ] **Step 2: Manual verification**

1. Open a feat/trait's description field and type a multi-word sentence at a normal pace, including natural pauses between words.
2. Confirm the field doesn't visibly refresh/lose your cursor position while you're still composing — it should only save ~3 seconds after you stop.
3. Repeat for an inventory item's description field.
4. Confirm the save still actually happens (wait 3+ seconds after your last keystroke, then reload the page and check your text persisted).

- [x] **Step 3: Leave uncommitted for review.**

**Flagging (not part of this task):** the underlying focus-loss-on-swap issue would still be there if someone pauses for 3+ seconds mid-sentence. If it's still noticeable after this change, the real fix is to stop replacing the focused input's DOM node on save (e.g. only swap the parts of the row that actually changed) — bigger change, only worth it if the timer bump isn't enough.

---

### Task 5: Move the rune divider above the description on feat/trait cards

**Root cause:** `misc/todos.txt` line 5 asks for the rune-divider graphic on feat/trait cards to sit above the description instead of below. [feat_row.html](templates/components/feats/feat_row.html) currently renders name → description → rune footer; the equivalent [inventory_row.html](templates/components/inventory/inventory_row.html) (not mentioned in the todo, leave as-is) has the same order and isn't being changed. `.card-item-footer` ([card_item.css:93-108](static/css/card_item.css#L93-L108)) is a plain flex-column item with no `order` property, so this is a pure DOM-order change — no CSS needed.

**Files:**
- Modify: `templates/components/feats/feat_row.html`

**Interfaces:** None — template-only reorder, same elements/ids/classes.

- [x] **Step 1: Move the footer block above the description block**

Current file:

```html
<div id="feat-row-{{ feat.id }}" class="card-item-row card-item-saved-row">
    <div id="feat-name-wrapper-{{ feat.id }}" class="card-item-field card-item-name-field card-item-name-wrapper section-row-indicator" hx-indicator="#feat-name-wrapper-{{ feat.id }}">
        <input type="text" id="feat_and_trait-name-{{ feat.id }}"
               name="feat_and_trait-name-{{ feat.id }}" value="{{ feat.name }}" class="field-input card-item-input feat-name-input"
               data-feat-id="{{ feat.id }}">
        <button type="button" id="feat-and-trait-delete-{{ feat.id }}" class="section-remove-x" data-feat-remove="true"
                hx-post="/characters/{{ character_id }}/feat-and-trait/{{ feat.id }}/remove"
                hx-target="#feats-section-container"
                hx-swap="innerHTML"
                hx-include="closest form"
                aria-label="Remove feat">&times;</button>
        <i class="bi bi-arrow-repeat section-row-spinner" aria-hidden="true"></i>
    </div>

    <div class="card-item-field card-item-description-field">
        <textarea id="feat_and_trait-description-{{ feat.id }}"
                  name="feat_and_trait-description-{{ feat.id }}" rows="1" class="field-input card-item-input card-item-description-input feat-description-input"
                  data-feat-id="{{ feat.id }}">{{ feat.description or '' }}</textarea>
    </div>

    <div class="card-item-footer" aria-hidden="true">
        {% include 'components/ui/rune_partition.html' %}
    </div>
</div>
```

Becomes (the footer `<div>` moved to between the name wrapper and the description field, nothing inside either block changed):

```html
<div id="feat-row-{{ feat.id }}" class="card-item-row card-item-saved-row">
    <div id="feat-name-wrapper-{{ feat.id }}" class="card-item-field card-item-name-field card-item-name-wrapper section-row-indicator" hx-indicator="#feat-name-wrapper-{{ feat.id }}">
        <input type="text" id="feat_and_trait-name-{{ feat.id }}"
               name="feat_and_trait-name-{{ feat.id }}" value="{{ feat.name }}" class="field-input card-item-input feat-name-input"
               data-feat-id="{{ feat.id }}">
        <button type="button" id="feat-and-trait-delete-{{ feat.id }}" class="section-remove-x" data-feat-remove="true"
                hx-post="/characters/{{ character_id }}/feat-and-trait/{{ feat.id }}/remove"
                hx-target="#feats-section-container"
                hx-swap="innerHTML"
                hx-include="closest form"
                aria-label="Remove feat">&times;</button>
        <i class="bi bi-arrow-repeat section-row-spinner" aria-hidden="true"></i>
    </div>

    <div class="card-item-footer" aria-hidden="true">
        {% include 'components/ui/rune_partition.html' %}
    </div>

    <div class="card-item-field card-item-description-field">
        <textarea id="feat_and_trait-description-{{ feat.id }}"
                  name="feat_and_trait-description-{{ feat.id }}" rows="1" class="field-input card-item-input card-item-description-input feat-description-input"
                  data-feat-id="{{ feat.id }}">{{ feat.description or '' }}</textarea>
    </div>
</div>
```

- [ ] **Step 2: Manual verification**

1. Open a character sheet with at least one feat/trait card, and add one if there are none.
2. Confirm the rune graphic now renders directly under the name row and above the description textarea.
3. Confirm the inventory cards are unchanged (rune still below the description there).
4. Add a new feat via the "+ Add" row and confirm the newly-added card also shows the rune above the description (it re-renders through the same template).

- [x] **Step 3: Leave uncommitted for review.**

---

### Task 6: Fix passive stats and proficiency toggles breaking after applying a custom buff

**Root cause:** `misc/todos.txt` line 7 ("applying a tracker" — actually the Custom Buffs section, the only feature that both toggles a modifier onto a stat *and* is added/edited/removed as a discrete action the way "applying" suggests) says passive fields reset to 0 and proficiency toggles stop responding until a refresh.

When a buff is added, edited, or removed, the server response ([buff_change_response.html](templates/components/buffs/buff_change_response.html)) swaps four containers: `custom-buffs-section-container` (the actual HTMX request target) plus three **out-of-band** swaps — `character-info-section-container`, `abilities-section-container`, and `custom-stats-section-container`. HTMX only fires `htmx:afterSwap` once, for the real target; the three OOB containers get fresh DOM nodes with none of their input listeners re-attached.

The `htmx:afterSwap` handler in `dnd_sheet.js` already has a branch per container ([dnd_sheet.js:166-300](static/scripts/dnd_sheet.js#L166-L300)) that knows exactly what each one needs when it's the *direct* target — e.g. the `abilities-section-container` branch calls `bindAbilityAutoSave()` and `recomputePassiveStats()`. The `custom-buffs-section-container` branch ([dnd_sheet.js:283-292](static/scripts/dnd_sheet.js#L283-L292)) never calls those, because normally nothing else needs to change when *that* branch runs — except after a buff action, when it's fanning out to three containers that do.

**Files:**
- Modify: `static/scripts/dnd_sheet.js:283-292`

**Interfaces:** None — calls only pre-existing, already-idempotent functions (`bindAbilityAutoSave`, `bindCharacterInfoAutoSave`, `bindCustomStatAutoSave`, `bindAddStatButton`, `recomputePassiveStats` all guard themselves with `dataset.xBound` checks or are safe to re-run).

- [x] **Step 1: Add the missing rebinds**

At [dnd_sheet.js:283-292](static/scripts/dnd_sheet.js#L283-L292):

```javascript
if (target.id === 'custom-buffs-section-container') {
    selectCustomBuffField();
    bindProficiencyToggles();
    syncGlobalLockState();
    bindCurrentHpCalculation();
    bindBuffCardEdit();
    decorateBuffedLabels();
    showGlobalFeedback('', 'success');
    return;
}
```

becomes:

```javascript
if (target.id === 'custom-buffs-section-container') {
    selectCustomBuffField();
    bindProficiencyToggles();
    syncGlobalLockState();
    bindCurrentHpCalculation();
    bindBuffCardEdit();
    decorateBuffedLabels();
    // ponytail: buff_change_response.html OOB-swaps abilities-section-container,
    // character-info-section-container and custom-stats-section-container
    // alongside this one, but htmx:afterSwap only fires for the direct target —
    // those three never get their own rebind branch below run. Re-bind what they
    // need here. If that template's OOB list ever grows, mirror it here too;
    // if this keeps happening for other templates, it's worth switching to a
    // shared htmx:oobAfterSwap-driven rebind map instead of per-branch copies.
    bindAbilityAutoSave();
    bindCharacterInfoAutoSave();
    bindCustomStatAutoSave();
    bindAddStatButton();
    recomputePassiveStats();
    showGlobalFeedback('', 'success');
    return;
}
```

- [ ] **Step 2: Manual verification**

1. Open a character with at least one skill proficiency toggled on, and note its passive value (e.g. passive Perception) and its current skill modifier.
2. Add a new custom buff targeting an ability or skill (Custom Buffs section → Add).
3. Immediately after it's added — without reloading — confirm the passive stat values are still correct (not reset to a bare "10").
4. Click a proficiency toggle on any skill and confirm it visibly flips **and** that leaving/reopening the sheet (or checking the network tab for the autosave POST) shows the change actually saved — not just a visual flip that reverts on refresh.
5. Edit the buff you just added (click its card, change its value, save) and repeat steps 3-4.
6. Remove the buff and repeat steps 3-4 once more.

- [x] **Step 3: Leave uncommitted for review.**

---

## Self-Review

**Spec coverage:**
- Dependency-loading fragility (my earlier diagnosis) → Task 1 (vendoring) + Task 2 (init isolation). Covered.
- `misc/todos.txt` line 1 (auth theme colours) → Task 3. Covered.
- `misc/todos.txt` line 3 (feat/inventory typing debounce) → Task 4. Covered.
- `misc/todos.txt` line 5 (rune position) → Task 5. Covered.
- `misc/todos.txt` line 7 (tracker/buff breaking passive stats + proficiency) → Task 6. Covered.

**Placeholder scan:** no TBDs; every step shows the actual before/after code or an exact shell command.

**Type/name consistency:** `safeBind` (Task 2) takes a bare function reference everywhere it's used; `CARD_ITEM_AUTO_SAVE_DEBOUNCE_MS` (Task 4) is defined once and used at both its call sites; the container-branch edit in Task 6 only calls functions that already exist elsewhere in the file under those exact names.

---

## Follow-up: closing the two flagged ceilings

Both "what I'm flagging" items from the original plan turned out to be worth closing immediately rather than waiting for a resurface — implemented after the six tasks above, same session.

### Follow-up A: `hx-preserve` instead of a longer timer (closes Task 4's real gap)

Task 4 only made the outerHTML swap on feat/inventory autosave happen less often; it didn't stop the swap from replacing the focused input's DOM node (and dropping focus/cursor) when it does fire. htmx ships a native mechanism for exactly this: `hx-preserve` on an element tells htmx to keep the *existing* live DOM node (by id) instead of swapping in the freshly-rendered one, confirmed by reading the vendored `htmx-1.9.12.min.js`'s implementation directly.

**Files:** `templates/components/feats/feat_row.html`, `templates/components/inventory/inventory_row.html` — added `hx-preserve="true"` to the name `<input>` and description `<textarea>` in both.

**Manual verification:** type a multi-word sentence into a feat/inventory description with natural pauses; the field should never visibly flicker or lose cursor position, even before the 3s debounce fires (this now holds regardless of timing, not just because of Task 4's longer delay).

### Follow-up B: a shared `htmx:oobAfterSwap` rebind table (closes Task 6's real gap)

Task 6 patched only the `custom-buffs-section-container` branch. The actual gap is structural: htmx fires `htmx:afterSwap` once, for the direct request target — a container swapped in as an out-of-band (`hx-swap-oob`) passenger on that same response never gets that event at all; htmx fires a separate `htmx:oobAfterSwap` for each OOB element instead, which this app never listened for.

Auditing every `hx-swap-oob` template in the app for what its OOB companions actually need turned up three more real (not hypothetical) instances of the same bug, all currently live:
- A class-level save OOB-swaps `custom-stats-section-container` and `tracker-page-container`, but the class-level save's own rebind branch never called `bindCustomStatAutoSave()`/`bindAddStatButton()` or `bindTrackerAutoSave()` — those inputs' autosave listeners go stale after any class-level edit.
- The same save also OOB-swaps `combat-stats-section-container` without calling `bindCurrentHpCalculation()` — temp HP / current HP / damage-health inputs stop responding.
- A character-info save OOB-swaps `abilities-section-container` without calling `bindAbilityAutoSave()` — ability scores stop live-recomputing their modifier after any character-info edit — and OOB-swaps `delete-character-dropdown` without calling `bindDeleteConfirmInput()`, so the "type DELETE to confirm" input stops enabling its confirm button after any character-info autosave.

**Files:** `static/scripts/dnd_sheet.js` — added an `OOB_CONTAINER_REBIND` table (container id → its safe-to-repeat rebind calls, covering every container this app currently OOB-swaps anywhere) plus a `rebindOobContainer()` helper and a `htmx:oobAfterSwap` listener that looks a swapped container up in that table. Removed the Task 6 special case from the `custom-buffs-section-container` branch, since the general listener now covers it (and everything else) for any caller, not just buffs.

**Manual verification:**
1. Edit a character's name/race (character-info) and wait for autosave; then edit an ability score and confirm its modifier still live-updates, and open the delete-character dropdown and confirm typing "DELETE" still enables the confirm button.
2. Add or change a class's level and wait for autosave; then edit a custom stat and confirm it still saves, use the "+ Add Stat" button, and adjust Temp HP / Current HP and confirm they still respond.
3. Repeat the original Task 6 buff-flow check (add/edit/remove a custom buff, confirm passive stats and proficiency toggles keep working).

**What's still not covered:** `add-class-action-container` and `add-stat-action-container` are in the table for completeness, but were already working before this fix (their "+ Add" buttons are re-bound as a side effect of their primary-target branches already running on the same response). Every other OOB-swapped container in the app either has no interactive listeners to lose (static text, a disabled display field, a plain link) or is covered above — this was a full audit of every `hx-swap-oob` template in the codebase, not a partial one.
