window.addEventListener("load", () => {
    initializeUiBindings();
    bindDeleteCharacterDropdown();
    bindSubBarTabs();
    bindThemePanel();

    const reopenAuthDropdownIfError = () => {
        const authDropdown = document.getElementById('auth-dropdown');
        if (!authDropdown || !authDropdown.querySelector('.auth-error')) {
            return false;
        }

        const toggle = authDropdown.querySelector('.dropdown-toggle');
        if (!toggle) {
            return false;
        }

        const dropdown = bootstrap.Dropdown.getOrCreateInstance(toggle);
        requestAnimationFrame(() => {
            dropdown.show();
        });
        return true;
    };

    // Inject the CSRF token into every htmx AJAX request as a header.
    // Flask-WTF's CSRFProtect accepts tokens from the X-CSRFToken header,
    document.body.addEventListener('htmx:configRequest', (event) => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            event.detail.headers['X-CSRFToken'] = meta.getAttribute('content');
        }
    });

    // Show a loading spinner in the global toast the instant any htmx request
    // starts, so add/save actions get immediate feedback instead of appearing
    // to do nothing until the response swaps in.
    document.body.addEventListener('htmx:beforeRequest', () => {
        showGlobalFeedback('', 'loading');
    });

    // Keep capacity controls in sync after HTMX swaps settle.
    document.body.addEventListener('htmx:afterSettle', (event) => {
        if (event.detail.successful === false) {
            return;
        }

        const trigger = event.detail.elt;
        if (trigger && trigger.dataset.featRemove === 'true') {
            syncFeatCapacityVisibility();
        }
        if (trigger && trigger.dataset.inventoryRemove === 'true') {
            syncInventoryCapacityVisibility();
        }
        if (trigger && trigger.dataset.inventoryDelete === 'true') {
            syncInventoryCapacityVisibility();
        }
    });

    document.body.addEventListener('htmx:afterSwap', (event) => {
        const target = event.detail.target || event.target;
        if (!target || !target.id) {
            return;
        }

        // Re-open the auth dropdown if a validation error was returned.
        // Resolve the live DOM node after swap instead of using the event target,
        // because outerHTML swaps can leave the target reference stale.
        if (target.id === 'auth-dropdown' || target.id === 'auth-area') {
            reopenAuthDropdownIfError();
            return;
        }

        // After a validation-error swap on the delete dropdown, re-bind the
        // input listener so the confirm button toggles properly, and keep
        // the dropdown visible.
        if (target.id === 'delete-character-dropdown') {
            bindDeleteConfirmInput();
            target.classList.remove('d-none');
            return;
        }

        if (target.id === 'character-info-section-container') {
            bindCurrentHpCalculation();
            bindProficiencyToggles();
            bindTrackerToggles();
            syncGlobalLockState();
            decorateBuffedLabels();
            bindCharacterInfoAutoSave();
            recomputePassiveStats();

            // When a new character is saved for the first time, reveal the
            // rest of the sheet sections that were hidden during creation.
            // Guard on a persisted name so partial/failed saves do not reveal
            // the full sheet prematurely.
            const sheetContent = document.getElementById('sheet-content');
            const nameInput = document.getElementById('character-name');
            const hasSavedName = nameInput && String(nameInput.value || '').trim().length > 0;
            if (sheetContent && sheetContent.dataset.isNew === 'true' && hasSavedName) {
                sheetContent.dataset.isNew = 'false';
                document.querySelectorAll('.new-char-hidden').forEach(el => {
                    el.classList.remove('new-char-hidden');
                });
            }

            hydrateCharacterInfoFeedbackFromServer();
            return;
        }

        if (target.id === 'classes-section-container') {
            bindAddClassButton();
            bindClassLevelAutoSave();
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            bindHitDiceSteppers();
            syncGlobalLockState();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'feats-section-container') {
            selectFeatField();
            setTimeout(() => bindFeatDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindFeatAutoSave();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'feats-list' || target.id === 'add-feat-row') {
            // Clear and close the add-feat form after a successful add
            const nameInput = document.getElementById('feat_and_trait-name');
            const descInput = document.getElementById('feat_and_trait-description');
            if (nameInput) nameInput.value = '';
            if (descInput) descInput.value = '';
            const addFeatBtnWrapper = document.getElementById('add-feat-btn-wrapper');
            const addFeatFieldName = document.getElementById('add-feat-field-name');
            const addFeatFieldDescription = document.getElementById('add-feat-field-description');
            const addFeatSubmitBtnWrapper = document.getElementById('add-feat-submit-btn-wrapper');
            const closeFeatBtnWrapper = document.getElementById('close-feat-btn-wrapper');
            if (addFeatBtnWrapper) addFeatBtnWrapper.style.display = 'flex';
            if (addFeatFieldName) addFeatFieldName.style.display = 'none';
            if (addFeatFieldDescription) addFeatFieldDescription.style.display = 'none';
            if (addFeatSubmitBtnWrapper) addFeatSubmitBtnWrapper.style.display = 'none';
            if (closeFeatBtnWrapper) closeFeatBtnWrapper.style.display = 'none';

            syncFeatCapacityVisibility();
            setTimeout(() => bindFeatDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindFeatAutoSave();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        // Individual feat row update (outerHTML swap)
        if (target.id && target.id.startsWith('feat-row-')) {
            setTimeout(() => bindFeatDescriptionDisplayAutoHeight(), 0);
            bindFeatAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'abilities-section-container') {
            bindAbilityAutoSave();
            bindProficiencyToggles();
            syncGlobalLockState();
            decorateBuffedLabels();
            recomputePassiveStats();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id && target.id.startsWith('ability-row-')) {
            bindAbilityAutoSave();
            bindProficiencyToggles();
            syncGlobalLockState();
            decorateBuffedLabels();
            recomputePassiveStats();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'inventory-section-container') {
            selectInventoryField();
            setTimeout(() => bindInventoryDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindInventoryAutoSave();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'inventory-list' || target.id === 'add-inventory-row') {
            // Clear and close the add-inventory form after a successful add
            const nameInput = document.getElementById('inventory-name');
            const descInput = document.getElementById('inventory-description');
            const qtyInput = document.getElementById('inventory-quantity');
            if (nameInput) nameInput.value = '';
            if (descInput) descInput.value = '';
            if (qtyInput) qtyInput.value = '1';
            const addInventoryBtnWrapper = document.getElementById('add-inventory-btn-wrapper');
            const addInventoryFieldName = document.getElementById('add-inventory-field-name');
            const addInventoryFieldQuantity = document.getElementById('add-inventory-field-quantity');
            const addInventoryFieldDescription = document.getElementById('add-inventory-field-description');
            const addInventorySubmitBtnWrapper = document.getElementById('add-inventory-submit-btn-wrapper');
            const closeInventoryBtnWrapper = document.getElementById('close-inventory-btn-wrapper');
            if (addInventoryBtnWrapper) addInventoryBtnWrapper.style.display = 'flex';
            if (addInventoryFieldName) addInventoryFieldName.style.display = 'none';
            if (addInventoryFieldQuantity) addInventoryFieldQuantity.style.display = 'none';
            if (addInventoryFieldDescription) addInventoryFieldDescription.style.display = 'none';
            if (addInventorySubmitBtnWrapper) addInventorySubmitBtnWrapper.style.display = 'none';
            if (closeInventoryBtnWrapper) closeInventoryBtnWrapper.style.display = 'none';

            syncInventoryCapacityVisibility();
            setTimeout(() => bindInventoryDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindInventoryAutoSave();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        // Individual inventory row update (outerHTML swap)
        if (target.id && target.id.startsWith('inventory-row-')) {
            syncInventoryCapacityVisibility();
            setTimeout(() => bindInventoryDescriptionDisplayAutoHeight(), 0);
            bindInventoryAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        // Quantity-only update (outerHTML swap on the qty control div)
        if (target.id && target.id.startsWith('inventory-qty-control-')) {
            syncGlobalLockState();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'tracker-page-container') {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            syncGlobalLockState();
            bindTrackerAutoSave();
            showGlobalFeedback('', 'success');
            return;
        }

        // Individual tracker item update (outerHTML swap)
        if (target.id && target.id.startsWith('tracker-item-')) {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            syncGlobalLockState();
            bindTrackerAutoSave();
            showGlobalFeedback('', 'success');
            return;
        }

        // Individual custom stat row update (outerHTML swap)
        if (target.id && target.id.startsWith('custom-stat-row-')) {
            bindCustomStatAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'custom-stats-section-container') {
            bindAddStatButton();
            syncGlobalLockState();
            bindCustomStatAutoSave();
            selectCustomBuffField();
            bindBuffCardEdit();
            decorateBuffedLabels();
            showGlobalFeedback('', 'success');
            return;
        }

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

        if (target.id === 'combat-stats-section-container') {
            bindCurrentHpCalculation();
            syncGlobalLockState();
            showGlobalFeedback('', 'success');
            return;
        }

        if (target.id === 'hit-dice-section-container') {
            bindHitDiceSteppers();
            syncGlobalLockState();
            showGlobalFeedback('', 'success');
            return;
        }
    });

    document.body.addEventListener('htmx:responseError', () => {
        showGlobalFeedback('Something went wrong. Please try again.', 'error');
    });

    document.body.addEventListener('htmx:sendError', () => {
        showGlobalFeedback('Something went wrong. Please try again.', 'error');
    });

    // Combat values can be changed by HTMX swaps (including OOB fragments)
    // without emitting user input events, so re-apply state classes here.
    document.body.addEventListener('htmx:afterSettle', (event) => {
        applyCombatStateColours();
        bindAllOptimisticRemoveButtons();

        // Safety net: a few afterSwap targets (auth dropdown, delete-character
        // dropdown, character info) drive their own feedback UI and never call
        // showGlobalFeedback, so the loading spinner would otherwise be stuck.
        const feedback = getGlobalFeedbackElement();
        if (feedback && feedback.classList.contains('is-loading')) {
            showGlobalFeedback('', event.detail.successful === false ? 'error' : 'success');
        }
    });
})

let featDescriptionResizeWindowBound = false;
let inventoryDescriptionResizeWindowBound = false;
const ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 5;
const CURRENT_HP_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;
const CHARACTER_INFO_FEEDBACK_HIDE_MS = 3000;
const GLOBAL_FEEDBACK_HIDE_MS = 3000;
const GLOBAL_ERROR_FEEDBACK_TEXT = 'Please try again';
const feedbackHideTimers = new Map();

// ── Debounced auto-save helper ───────────────────────────────────────────────
const AUTO_SAVE_DEBOUNCE_MS = 1500;

function createDebouncedSaver(delayMs = AUTO_SAVE_DEBOUNCE_MS) {
    const timers = new Map();

    function cancel(key) {
        const existing = timers.get(key);
        if (existing) {
            clearTimeout(existing);
        }
        timers.delete(key);
    }

    function schedule(key, fn) {
        cancel(key);
        timers.set(key, setTimeout(() => {
            timers.delete(key);
            fn();
        }, delayMs));
    }

    function flush(key, fn) {
        if (!timers.has(key)) {
            return false;
        }
        cancel(key);
        fn();
        return true;
    }

    function hasPending(key) {
        return timers.has(key);
    }

    return { schedule, flush, cancel, hasPending };
}

// ── Optimistic remove (× buttons) ────────────────────────────────────────────
// Every remove button in this app swaps its *whole* section container via
// hx-swap="innerHTML" once the server responds — so hiding the clicked row's
// DOM node immediately, then letting the existing hx-post fire as normal, is
// enough: whatever lands from the server (success or failure) replaces the
// entire container's children wholesale, discarding the temporarily-hidden
// node either way. No reconciliation or rollback state needed.
function bindOptimisticRemoveButtons(container, buttonSelector, rowSelector) {
    if (!container) return;
    container.querySelectorAll(buttonSelector).forEach((button) => {
        if (button.dataset.optimisticRemoveBound === 'true') return;
        button.dataset.optimisticRemoveBound = 'true';
        button.addEventListener('click', () => {
            const row = button.closest(rowSelector);
            if (row) row.style.display = 'none';
        });
    });
}

function bindAllOptimisticRemoveButtons() {
    bindOptimisticRemoveButtons(document.getElementById('feats-section-container'), '[data-feat-remove="true"]', '.card-item-saved-row');
    bindOptimisticRemoveButtons(document.getElementById('inventory-section-container'), '[data-inventory-delete="true"]', '.card-item-saved-row');
    bindOptimisticRemoveButtons(document.getElementById('custom-stats-section-container'), '[data-custom-stat-remove="true"]', '.custom-stats-section-row');
    bindOptimisticRemoveButtons(document.getElementById('classes-section-container'), '[data-class-remove="true"]', '.classes-section-row');
    bindOptimisticRemoveButtons(document.getElementById('custom-buffs-section-container'), '[data-buff-remove="true"]', '.custom-buffs-card');
    bindOptimisticRemoveButtons(document.getElementById('tracker-page-container'), '[data-tracker-remove="true"]', '.tracker-item');
    bindOptimisticRemoveButtons(document.getElementById('tracker-page-container'), '[data-tracker-entry-remove="true"]', '.tracker-entry-row');
}

function getCharacterInfoFeedbackElement() {
    return document.getElementById('character-info-feedback');
}

function getGlobalFeedbackElement() {
    return document.getElementById('global-feedback');
}

function clearFeedbackHideTimer(feedbackId) {
    if (!feedbackId) {
        return;
    }

    const existingTimer = feedbackHideTimers.get(feedbackId);
    if (existingTimer) {
        clearTimeout(existingTimer);
        feedbackHideTimers.delete(feedbackId);
    }
}

function resetFeedbackElement(feedback, { resetDataset = false } = {}) {
    if (!feedback) {
        return;
    }

    clearFeedbackHideTimer(feedback.id);
    feedback.replaceChildren();
    feedback.classList.remove('is-visible', 'is-success', 'is-error', 'is-loading');
    feedback.removeAttribute('aria-label');

    if (resetDataset) {
        feedback.dataset.feedbackKind = '';
        feedback.dataset.feedbackMessage = '';
    }
}

function armFeedbackAutoHide(feedback, hideMs, clearFn) {
    if (!feedback || !feedback.classList.contains('is-visible')) {
        return;
    }

    const feedbackId = feedback.id;
    if (!feedbackId) {
        return;
    }

    clearFeedbackHideTimer(feedbackId);
    feedbackHideTimers.set(feedbackId, setTimeout(() => {
        clearFn();
    }, hideMs));
}

function renderFeedbackElement(feedback, {
    kind = 'success',
    message = '',
    successIconClass = '',
    errorIconClass = successIconClass,
    loadingIconClass = successIconClass,
    textClass = '',
    successAriaLabel = 'Saved',
    loadingAriaLabel = 'Saving',
    errorMessageOverride = '',
    updateDataset = false,
} = {}) {
    if (!feedback) {
        return {
            isError: kind === 'error',
            safeMessage: '',
            renderedMessage: '',
        };
    }

    const isError = kind === 'error';
    const isLoading = kind === 'loading';
    const safeMessage = String(message || '').trim();
    const overrideMessage = String(errorMessageOverride || '').trim();
    const renderedMessage = isError ? (overrideMessage || safeMessage) : safeMessage;

    resetFeedbackElement(feedback, { resetDataset: updateDataset });

    if (isError && !renderedMessage) {
        return { isError, safeMessage, renderedMessage };
    }

    const icon = document.createElement('i');
    icon.className = isError
        ? `bi bi-exclamation-circle-fill ${errorIconClass}`.trim()
        : isLoading
            ? `bi bi-arrow-repeat ${loadingIconClass}`.trim()
            : `bi bi-check-circle-fill ${successIconClass}`.trim();
    icon.setAttribute('aria-hidden', 'true');
    feedback.appendChild(icon);

    feedback.setAttribute('aria-label', isError ? renderedMessage : (isLoading ? loadingAriaLabel : successAriaLabel));

    if (renderedMessage) {
        const messageNode = document.createElement('span');
        messageNode.className = textClass;
        messageNode.textContent = renderedMessage;
        feedback.appendChild(messageNode);
    }

    if (updateDataset) {
        feedback.dataset.feedbackKind = isError ? 'error' : (isLoading ? 'loading' : 'success');
        feedback.dataset.feedbackMessage = safeMessage;
    }

    feedback.classList.add('is-visible');
    feedback.classList.remove('is-success', 'is-error', 'is-loading');
    feedback.classList.add(isError ? 'is-error' : (isLoading ? 'is-loading' : 'is-success'));

    return { isError, safeMessage, renderedMessage };
}

function clearGlobalFeedback() {
    clearFeedbackHideTimer('global-feedback');
    const feedback = getGlobalFeedbackElement();
    resetFeedbackElement(feedback);
}

function armGlobalFeedbackAutoHide() {
    const feedback = getGlobalFeedbackElement();
    armFeedbackAutoHide(feedback, GLOBAL_FEEDBACK_HIDE_MS, clearGlobalFeedback);
}

function showGlobalFeedback(message, kind = 'success') {
    const feedback = getGlobalFeedbackElement();
    if (!feedback) {
        return;
    }

    renderFeedbackElement(feedback, {
        kind,
        message,
        successIconClass: 'global-feedback-icon feedback-message-icon',
        errorIconClass: 'global-feedback-icon feedback-message-icon',
        loadingIconClass: 'global-feedback-icon feedback-message-icon',
        textClass: 'global-feedback-text feedback-message-text',
        successAriaLabel: 'Saved',
        loadingAriaLabel: 'Saving',
        errorMessageOverride: GLOBAL_ERROR_FEEDBACK_TEXT,
    });

    // Loading persists until a real completion event replaces it — don't auto-hide it.
    if (kind !== 'loading') {
        armGlobalFeedbackAutoHide();
    }
}

function clearCharacterInfoFeedback() {
    clearFeedbackHideTimer('character-info-feedback');
    const feedback = getCharacterInfoFeedbackElement();
    resetFeedbackElement(feedback, { resetDataset: true });
}

function armCharacterInfoFeedbackAutoHide() {
    const feedback = getCharacterInfoFeedbackElement();
    armFeedbackAutoHide(feedback, CHARACTER_INFO_FEEDBACK_HIDE_MS, clearCharacterInfoFeedback);
}

function showCharacterInfoFeedback(message, kind = 'success') {
    showGlobalFeedback(message, kind);
}

function hydrateCharacterInfoFeedbackFromServer() {
    const feedback = getCharacterInfoFeedbackElement();
    if (!feedback) {
        return;
    }

    const feedbackKind = String(feedback.dataset.feedbackKind || '').trim();
    const feedbackMessage = String(feedback.dataset.feedbackMessage || '').trim();

    if (feedbackKind === 'success') {
        showCharacterInfoFeedback('', 'success');
        return;
    }

    if (feedbackKind === 'error' && feedbackMessage) {
        showCharacterInfoFeedback(feedbackMessage, 'error');
        return;
    }

    if (feedback.classList.contains('is-visible')) {
        armCharacterInfoFeedbackAutoHide();
    }
}

function getHtmxRequestPath(detail) {
    if (!detail) {
        return '';
    }

    const requestConfigPath = detail.requestConfig && detail.requestConfig.path;
    if (requestConfigPath) {
        return String(requestConfigPath);
    }

    const requestPath = detail.pathInfo && detail.pathInfo.requestPath;
    if (requestPath) {
        return String(requestPath);
    }

    const xhr = detail.xhr;
    if (xhr && typeof xhr.responseURL === 'string') {
        try {
            return new URL(xhr.responseURL, window.location.origin).pathname;
        } catch (_) {
            return xhr.responseURL;
        }
    }

    return '';
}

function isCharacterInfoFragmentRequest(detail) {
    const requestPath = getHtmxRequestPath(detail);
    return requestPath.includes('/character-info/fragment');
}

function getCookieValue(name) {
    const encodedName = encodeURIComponent(name);
    const cookiePairs = document.cookie ? document.cookie.split('; ') : [];

    for (const cookiePair of cookiePairs) {
        const separatorIndex = cookiePair.indexOf('=');
        if (separatorIndex < 0) {
            continue;
        }

        const cookieName = cookiePair.slice(0, separatorIndex);
        if (cookieName !== encodedName) {
            continue;
        }

        const cookieValue = cookiePair.slice(separatorIndex + 1);
        return decodeURIComponent(cookieValue);
    }

    return null;
}

function setCookieValue(name, value, maxAgeSeconds) {
    const encodedName = encodeURIComponent(name);
    const encodedValue = encodeURIComponent(value);
    document.cookie = `${encodedName}=${encodedValue}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

function applyCombatStateColours(fields = {}) {
    const healthPointsField = fields.healthPointsField || document.getElementById('character-health_points');
    const tempHpField = fields.tempHpField || document.getElementById('character-temporary_hit_points');
    const currentHpField = fields.currentHpField || document.getElementById('character-current_health_points');

    if (!healthPointsField || !tempHpField || !currentHpField) {
        return;
    }

    const parseNumberOrZero = (value) => {
        if (value === '--' || value === '') return 0;
        const parsed = Number.parseInt(value, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const tempHp = Math.max(0, parseNumberOrZero(tempHpField.value));
    const healthPoints = Math.max(0, parseNumberOrZero(healthPointsField.value));
    const currentHp = Math.max(0, parseNumberOrZero(currentHpField.value));
    const criticalThreshold = healthPoints / 4;

    tempHpField.classList.toggle('combat-success-state', tempHp > 0);
    currentHpField.classList.toggle('combat-critical-state', healthPoints > 0 && currentHp <= criticalThreshold);
}

// ── Delete-character dropdown ────────────────────────────────────────────────

/**
 * Wire up the toggle button to show/hide the confirmation dropdown,
 * and close it when clicking outside.
 */
function bindDeleteCharacterDropdown() {
    const toggle = document.getElementById('delete-character-toggle');
    if (!toggle || toggle.dataset.bound === 'true') return;
    toggle.dataset.bound = 'true';

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        const dropdown = document.getElementById('delete-character-dropdown');
        if (!dropdown) return;

        dropdown.classList.toggle('d-none');

        // Focus the input when opening
        if (!dropdown.classList.contains('d-none')) {
            const input = dropdown.querySelector('#delete-confirm-input');
            if (input) input.focus();
        }
    });

    if (document.body.dataset.deleteDropdownDocBound !== 'true') {
        document.body.dataset.deleteDropdownDocBound = 'true';
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('delete-character-dropdown');
            const liveToggle = document.getElementById('delete-character-toggle');
            if (!dropdown || !liveToggle) {
                return;
            }
            if (!dropdown.contains(e.target) && !liveToggle.contains(e.target)) {
                dropdown.classList.add('d-none');
            }
        });
    }

    bindDeleteConfirmInput();
}

/**
 * Enable the confirm button only when the input value is exactly "DELETE".
 */
function bindDeleteConfirmInput() {
    const input = document.getElementById('delete-confirm-input');
    const btn = document.getElementById('delete-confirm-btn');
    if (!input || !btn || input.dataset.bound === 'true') return;
    input.dataset.bound = 'true';

    input.addEventListener('input', () => {
        if (input.value.trim() === 'DELETE') {
            btn.removeAttribute('disabled');
        } else {
            btn.setAttribute('disabled', '');
        }
    });
}

function initializeUiBindings() {
    bindAddClassButton();
    bindAddStatButton();
    selectFeatField();
    selectInventoryField();
    selectCustomBuffField();
    bindClassLevelAutoSave();
    bindCustomStatAutoSave();
    bindProficiencyToggles();
    bindCurrentHpCalculation();
    bindBuffCardEdit();
    bindFeatDescriptionDisplayAutoHeight();
    bindInventoryDescriptionDisplayAutoHeight();
    decorateBuffedLabels();
    bindCharacterInfoAutoSave();
    bindFeatAutoSave();
    bindInventoryAutoSave();
    bindAbilityAutoSave();
    recomputePassiveStats();
    bindFeatsContainerSettle();
    bindInventoryContainerSettle();
    bindAbilitiesContainerSettle();
    bindCharacterInfoContainerSettle();
    bindClassesContainerSettle();
    bindCustomStatsContainerSettle();
    bindGlobalLockToggle();
    bindTrackerAutoSave();
    bindTrackerToggles();
    bindAllOptimisticRemoveButtons();
    bindMobileCharacterSelect();
    bindAbilityStepButtons();
    bindHitDiceSteppers();
}

function bindMobileCharacterSelect() {
    const selector = document.getElementById('character-mobile-select');
    if (!selector || selector.dataset.bound === 'true') {
        return;
    }

    selector.dataset.bound = 'true';
    selector.addEventListener('change', () => {
        const selectedCharacterId = String(selector.value || '').trim();
        if (!selectedCharacterId || selectedCharacterId === '__unsaved__') {
            return;
        }
        window.location.assign(`/?character_id=${encodeURIComponent(selectedCharacterId)}`);
    });
}

const FEAT_TRAIT_MAX = 15;
const INVENTORY_MAX = 50;

function syncFeatCapacityVisibility() {
    const featsList = document.getElementById('feats-list');
    const addRow = document.querySelector('.feats-section .card-item-add-row');
    if (!featsList || !addRow) return;
    const count = featsList.querySelectorAll('.card-item-saved-row').length;
    addRow.style.display = count >= FEAT_TRAIT_MAX ? 'none' : '';
}

function syncInventoryCapacityVisibility() {
    const inventoryList = document.getElementById('inventory-list');
    const addRow = document.querySelector('.inventory-section .card-item-add-row');
    if (!inventoryList || !addRow) return;
    const count = inventoryList.querySelectorAll('.card-item-saved-row').length;
    addRow.style.display = count >= INVENTORY_MAX ? 'none' : '';
}

function bindFeatsContainerSettle() {
    const container = document.getElementById('feats-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';
    container.addEventListener('htmx:afterSettle', () => {
        setTimeout(() => {
            bindFeatDescriptionDisplayAutoHeight();
            bindFeatAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
        }, 0);
    });
    container.addEventListener('focusout', (event) => {
        const row = event.target.closest('.card-item-saved-row');
        if (!row) return;
        const stillInRow = event.relatedTarget && row.contains(event.relatedTarget);
        if (stillInRow) return;
        const featId = row.querySelector('.feat-name-input')?.dataset.featId;
        if (featId) featAutoSave.flush(featId, () => saveFeatRow(featId));
    });
    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushAllPendingFeats();
    });
}

function flushAllPendingFeats() {
    const container = document.getElementById('feats-section-container');
    if (!container) return;
    container.querySelectorAll('.card-item-saved-row').forEach((row) => {
        const featId = row.querySelector('.feat-name-input')?.dataset.featId;
        if (featId) featAutoSave.flush(featId, () => saveFeatRow(featId));
    });
}

function bindInventoryContainerSettle() {
    const container = document.getElementById('inventory-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';
    container.addEventListener('htmx:afterSettle', () => {
        setTimeout(() => {
            bindInventoryDescriptionDisplayAutoHeight();
            bindInventoryAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
        }, 0);
    });
    container.addEventListener('focusout', (event) => {
        const row = event.target.closest('.card-item-saved-row');
        if (!row) return;
        const stillInRow = event.relatedTarget && row.contains(event.relatedTarget);
        if (stillInRow) return;
        const inventoryId = row.querySelector('.inventory-name-input')?.dataset.inventoryId;
        if (inventoryId) inventoryAutoSave.flush(inventoryId, () => saveInventoryRow(inventoryId));
    });
    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushAllPendingInventory();
    });
}

function flushAllPendingInventory() {
    const container = document.getElementById('inventory-section-container');
    if (!container) return;
    container.querySelectorAll('.card-item-saved-row').forEach((row) => {
        const inventoryId = row.querySelector('.inventory-name-input')?.dataset.inventoryId;
        if (inventoryId) inventoryAutoSave.flush(inventoryId, () => saveInventoryRow(inventoryId));
    });
}

const featAutoSave = createDebouncedSaver();

function saveFeatRow(featId) {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const row = document.getElementById(`feat-row-${featId}`);
    if (!row) {
        return;
    }
    const nameInput = row.querySelector('.feat-name-input');
    const descInput = row.querySelector('.feat-description-input');
    if (!nameInput) {
        return;
    }

    htmx.ajax('POST', `/characters/${characterId}/feat-and-trait/${featId}/update`, {
        source: nameInput,
        target: `#feat-row-${featId}`,
        swap: 'outerHTML',
        values: {
            [`feat_and_trait-name-${featId}`]: nameInput.value,
            [`feat_and_trait-description-${featId}`]: descInput ? descInput.value : '',
        }
    });
}

function bindFeatAutoSave() {
    const featsSection = document.querySelector('.feats-section');
    if (!featsSection) {
        return;
    }

    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const rows = featsSection.querySelectorAll('.card-item-saved-row');

    rows.forEach((row) => {
        const nameInput = row.querySelector('.feat-name-input');
        const descInput = row.querySelector('.feat-description-input');
        if (!nameInput) return;

        const featId = nameInput.dataset.featId;
        if (!featId) return;

        const triggerAutoSave = () => featAutoSave.schedule(featId, () => saveFeatRow(featId));

        [nameInput, descInput].forEach((input) => {
            if (!input || input.dataset.autoSaveBound === 'true') return;
            input.dataset.autoSaveBound = 'true';
            input.addEventListener('input', triggerAutoSave);
        });
    });
}

const characterInfoAutoSave = createDebouncedSaver(1000);

function saveCharacterInfo() {
    const section = document.querySelector('.character-info-section');
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!section || !characterId) return;
    const form = section.closest('form');
    if (!form) return;
    htmx.ajax('POST', `/characters/${characterId}/character-info/fragment`, {
        source: form,
        target: '#character-info-section-container',
        swap: 'innerHTML'
    });
}

function bindCharacterInfoAutoSave() {
    const section = document.querySelector('.character-info-section');
    if (!section) {
        return;
    }

    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const inputs = section.querySelectorAll('input:not([type="hidden"]):not([disabled])');

    inputs.forEach((input) => {
        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', () => characterInfoAutoSave.schedule('character-info', saveCharacterInfo));
    });
}

function bindCharacterInfoContainerSettle() {
    const container = document.getElementById('character-info-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';

    container.addEventListener('focusout', (event) => {
        const section = event.target.closest('.character-info-section');
        if (!section) return;
        const stillInSection = event.relatedTarget && section.contains(event.relatedTarget);
        if (stillInSection) return;
        characterInfoAutoSave.flush('character-info', saveCharacterInfo);
    });

    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushPendingCharacterInfo();
    });
}

function flushPendingCharacterInfo() {
    characterInfoAutoSave.flush('character-info', saveCharacterInfo);
}

const classLevelAutoSave = createDebouncedSaver(1000);

function saveClassLevels() {
    const classesSection = document.querySelector('.classes-section');
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!classesSection || !characterId) return;
    const form = classesSection.closest('form');
    if (!form) return;
    htmx.ajax('POST', `/characters/${characterId}/classes/fragment`, {
        source: form,
        target: '#classes-section-container',
        swap: 'innerHTML'
    });
}

function bindClassLevelAutoSave() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const classesSection = document.querySelector('.classes-section');
    if (!classesSection) {
        return;
    }

    const inputs = classesSection.querySelectorAll('.class-level-input');

    inputs.forEach((input) => {
        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', () => classLevelAutoSave.schedule('class-level', saveClassLevels));
    });
}

function bindClassesContainerSettle() {
    const container = document.getElementById('classes-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';

    container.addEventListener('focusout', (event) => {
        const section = event.target.closest('.classes-section');
        if (!section) return;
        const stillInSection = event.relatedTarget && section.contains(event.relatedTarget);
        if (stillInSection) return;
        classLevelAutoSave.flush('class-level', saveClassLevels);
    });

    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushPendingClassLevels();
    });
}

function flushPendingClassLevels() {
    classLevelAutoSave.flush('class-level', saveClassLevels);
}

const customStatAutoSave = createDebouncedSaver(1000);

function saveCustomStatRow(statId) {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) return;
    const valueInput = document.getElementById(`custom_stat-value-${statId}`);
    const nameInput = document.getElementById(`custom_stat-name-${statId}`);
    if (!valueInput) return;
    htmx.ajax('POST', `/characters/${characterId}/custom-stat/${statId}/update`, {
        source: valueInput,
        target: `#custom-stat-row-${statId}`,
        swap: 'outerHTML',
        values: {
            [`custom_stat-value-${statId}`]: valueInput.value,
            [`custom_stat-name-${statId}`]: nameInput ? nameInput.value : '',
        }
    });
}

function bindCustomStatAutoSave() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const statsSection = document.querySelector('.custom-stats-section');
    if (!statsSection) {
        return;
    }

    const inputs = statsSection.querySelectorAll('.custom-stats-section-input[type="number"]');

    inputs.forEach((input) => {
        const statId = input.dataset.customStatId || input.id.replace('custom_stat-value-', '');
        if (!statId || !input.id.startsWith('custom_stat-value-')) {
            return;
        }

        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', () => customStatAutoSave.schedule(statId, () => saveCustomStatRow(statId)));
    });
}

function bindCustomStatsContainerSettle() {
    const container = document.getElementById('custom-stats-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';

    container.addEventListener('focusout', (event) => {
        const row = event.target.closest('.custom-stats-section-row');
        if (!row) return;
        const stillInRow = event.relatedTarget && row.contains(event.relatedTarget);
        if (stillInRow) return;
        const statId = row.querySelector('.custom-stats-section-input')?.dataset.customStatId;
        if (statId) customStatAutoSave.flush(statId, () => saveCustomStatRow(statId));
    });

    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushAllPendingCustomStats();
    });
}

function flushAllPendingCustomStats() {
    const container = document.getElementById('custom-stats-section-container');
    if (!container) return;
    container.querySelectorAll('.custom-stats-section-row').forEach((row) => {
        const statId = row.querySelector('.custom-stats-section-input')?.dataset.customStatId;
        if (statId) customStatAutoSave.flush(statId, () => saveCustomStatRow(statId));
    });
}

function bindBuffCardEdit() {
    const section = document.querySelector('.custom-buffs-section');
    if (!section) return;

    const addBtnWrapper = document.getElementById('add-custom-buff-btn-wrapper');
    const fieldsWrapper = document.getElementById('add-custom-buff-fields-wrapper');
    const submitBtnWrapper = document.getElementById('add-custom-buff-submit-btn-wrapper');
    const closeBtnWrapper = document.getElementById('close-custom-buff-btn-wrapper');
    const submitBtn = document.getElementById('custom-buff-add');
    const submitLabel = submitBtnWrapper ? submitBtnWrapper.querySelector('.section-action-label') : null;
    const nameInput = document.getElementById('custom_buff-name');
    const valueInput = document.getElementById('custom_buff-value');

    if (!submitBtn || !nameInput || !valueInput || !fieldsWrapper || !submitBtnWrapper || !closeBtnWrapper) {
        return;
    }

    // Store the original add URL so we can restore it when closing edit mode
    if (!submitBtn.dataset.originalUrl) {
        submitBtn.dataset.originalUrl = submitBtn.getAttribute('hx-post') || '';
    }
    const originalUrl = submitBtn.dataset.originalUrl;

    const tableCheckboxes = section.querySelectorAll('.custom-buffs-table-checkbox');
    const statCheckboxes = section.querySelectorAll('.custom-buffs-stat-checkbox');

    const resetToAddMode = () => {
        // Clear form fields
        nameInput.value = '';
        valueInput.value = '0';
        tableCheckboxes.forEach((cb) => { cb.checked = false; });
        statCheckboxes.forEach((cb) => { cb.checked = false; });

        // Restore the add URL and label
        submitBtn.setAttribute('hx-post', originalUrl);
        htmx.process(submitBtn);
        if (submitLabel) submitLabel.textContent = 'Add';
        section.dataset.editMode = 'false';
        section.dataset.editBuffId = '';
    };

    const cards = section.querySelectorAll('.custom-buffs-card[data-buff-edit="true"]');
    cards.forEach((card) => {
        if (card.dataset.editBound === 'true') return;
        card.dataset.editBound = 'true';

        card.addEventListener('click', (e) => {
            if (e.target.closest('[data-buff-remove="true"]')) return;
            if (section.dataset.locked === 'true') return;

            const buffId = card.dataset.buffId;
            const buffName = card.dataset.buffName;
            const buffValue = card.dataset.buffValue;

            // Clicking the currently selected buff toggles edit mode off.
            if (section.dataset.editMode === 'true' && section.dataset.editBuffId === String(buffId || '')) {
                const closeBtn = document.getElementById('close-custom-buff-field-x-btn');
                if (closeBtn) {
                    closeBtn.click();
                } else {
                    resetToAddMode();
                }
                return;
            }

            let buffTargets = [];
            try {
                buffTargets = JSON.parse(card.dataset.buffTargets || '[]');
            } catch (_) { /* ignore */ }

            // Populate name/value
            nameInput.value = buffName || '';
            valueInput.value = buffValue || '0';

            // Build sets of selected tables and stats
            const selectedTables = new Set();
            const selectedStatsByTable = {};
            for (const target of buffTargets) {
                const tableName = target.stat_table_name;
                if (tableName) {
                    selectedTables.add(tableName);
                    if (!selectedStatsByTable[tableName]) {
                        selectedStatsByTable[tableName] = new Set();
                    }
                    for (const statName of (target.stat_names || [])) {
                        selectedStatsByTable[tableName].add(statName);
                    }
                }
            }

            // Set table checkboxes
            tableCheckboxes.forEach((cb) => {
                cb.checked = selectedTables.has(cb.dataset.tableName);
            });

            // Set stat checkboxes
            statCheckboxes.forEach((cb) => {
                const tableName = cb.dataset.tableName;
                cb.checked = !!(selectedStatsByTable[tableName] && selectedStatsByTable[tableName].has(cb.value));
            });

            // Swap submit button to update mode
            const characterIdField = document.getElementById('character-id');
            const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
            if (characterId && buffId) {
                submitBtn.setAttribute('hx-post', `/characters/${characterId}/custom-buff/${buffId}/update`);
                htmx.process(submitBtn);
            }
            if (submitLabel) submitLabel.textContent = 'Save';
            section.dataset.editMode = 'true';
            section.dataset.editBuffId = String(buffId || '');

            // Show the form (same as clicking the + Add button)
            if (addBtnWrapper) addBtnWrapper.style.display = 'none';
            fieldsWrapper.style.display = 'flex';
            submitBtnWrapper.style.display = 'flex';
            closeBtnWrapper.style.display = 'flex';

            // Trigger the table stat groups to update visibility
            tableCheckboxes.forEach((cb) => {
                cb.dispatchEvent(new Event('change'));
            });
        });
    });

    // When the close button is clicked, reset back to add mode
    const closeBtn = document.getElementById('close-custom-buff-field-x-btn');
    if (closeBtn && closeBtn.dataset.editResetBound !== 'true') {
        closeBtn.dataset.editResetBound = 'true';
        closeBtn.addEventListener('click', () => {
            if (section.dataset.editMode === 'true') {
                resetToAddMode();
            }
        });
    }
}

function getGlobalLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }
    return `global_lock_${characterId}`;
}

function getGlobalLockState() {
    const cookieKey = getGlobalLockCookieKey();
    const persisted = cookieKey ? getCookieValue(cookieKey) : null;
    if (persisted === 'true') return true;
    return false;
}

function syncGlobalLockState() {
    const isLocked = getGlobalLockState();

    // ── Sub-bar lock button icon ──
    const lockBtn = document.getElementById('global-lock-toggle');
    if (lockBtn) {
        lockBtn.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockBtn.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockBtn.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
    }

    // ── Abilities section ──
    const abilitiesSection = document.querySelector('.abilities-section');
    if (abilitiesSection) {
        abilitiesSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('.abilities-section-name-input').forEach((input) => {
        if (isLocked) {
            input.setAttribute('readonly', '');
        } else {
            input.removeAttribute('readonly');
        }
    });
    document.querySelectorAll('.abilities-section-step-btn').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });

    // ── Character + Combat sections ──
    const characterInfoSection = document.querySelector('.character-info-section');
    if (characterInfoSection) {
        characterInfoSection.dataset.locked = String(isLocked);
    }
    const combatSection = document.querySelector('.combat-section');
    if (combatSection) {
        combatSection.dataset.locked = String(isLocked);
    }
    // The whole Combat section (Temp HP, Current HP, Damage/Health) and the
    // Hit Dice section are combat-tracking, not build fields — none of it
    // respects the lock.

    // ── Classes & custom stats section ──
    const statsSection = document.querySelector('.custom-stats-section');
    if (statsSection) {
        statsSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('[data-custom-stat-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });
    document.querySelectorAll('.custom-stats-section-input').forEach((input) => {
        if (isLocked) {
            input.setAttribute('readonly', '');
        } else {
            input.removeAttribute('readonly');
        }
    });
    document.querySelectorAll('[data-class-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });

    // ── Add Class action (lock-gated) ──
    const addClassContainer = document.getElementById('add-class-action-container');
    if (addClassContainer) {
        addClassContainer.style.display = isLocked ? 'none' : '';
        if (isLocked) {
            const w = document.getElementById('add-class-btn-wrapper');
            const d = document.getElementById('add-class-field-dropdown');
            const l = document.getElementById('add-class-field-level');
            const s = document.getElementById('add-class-submit-btn');
            const c = document.getElementById('close-add-class-btn-wrapper');
            if (w) w.style.display = '';
            if (d) d.style.display = 'none';
            if (l) l.style.display = 'none';
            if (s) s.style.display = 'none';
            if (c) c.style.display = 'none';
        }
    }

    // ── Add Stat action (lock-gated) ──
    const addStatContainer = document.getElementById('add-stat-action-container');
    if (addStatContainer) {
        addStatContainer.style.display = isLocked ? 'none' : '';
        if (isLocked) {
            const w = document.getElementById('add-custom-stat-btn-wrapper');
            const n = document.getElementById('add-custom-stat-field-name');
            const v = document.getElementById('add-custom-stat-field-value');
            const s = document.getElementById('add-custom-stat-submit-btn-wrapper');
            const c = document.getElementById('close-add-stat-btn-wrapper');
            if (w) w.style.display = '';
            if (n) n.style.display = 'none';
            if (v) v.style.display = 'none';
            if (s) s.style.display = 'none';
            if (c) c.style.display = 'none';
        }
    }

    // ── Add Feat row (lock-gated) ──
    const addFeatRow = document.getElementById('add-feat-row');
    if (addFeatRow) {
        addFeatRow.style.display = isLocked ? 'none' : '';
        if (isLocked) {
            const bw = document.getElementById('add-feat-btn-wrapper');
            const fn = document.getElementById('add-feat-field-name');
            const fd = document.getElementById('add-feat-field-description');
            const fs = document.getElementById('add-feat-submit-btn-wrapper');
            const fc = document.getElementById('close-feat-btn-wrapper');
            if (bw) bw.style.display = 'flex';
            if (fn) fn.style.display = 'none';
            if (fd) fd.style.display = 'none';
            if (fs) fs.style.display = 'none';
            if (fc) fc.style.display = 'none';
        }
    }

    // ── Feats section ──
    const featsSection = document.querySelector('.feats-section');
    if (featsSection) {
        featsSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('[data-feat-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });
    document.querySelectorAll('.feat-name-input, .feat-description-input').forEach((input) => {
        if (isLocked) {
            input.setAttribute('readonly', '');
        } else {
            input.removeAttribute('readonly');
        }
    });

    // ── Inventory section ──
    const inventorySection = document.querySelector('.inventory-section');
    if (inventorySection) {
        inventorySection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('.inventory-section [data-inventory-remove="true"]').forEach((button) => {
        const quantity = parseInt(button.dataset.itemQuantity, 10) || 0;
        const shouldDisable = isLocked && quantity <= 1;
        button.disabled = shouldDisable;
        button.setAttribute('aria-disabled', shouldDisable ? 'true' : 'false');
        const showTrash = !isLocked && quantity <= 1;
        button.innerHTML = showTrash
            ? '<i class="bi bi-trash-fill" aria-hidden="true" style="font-size:0.75em;"></i>'
            : '−';
    });
    document.querySelectorAll('[data-inventory-delete="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });
    document.querySelectorAll('.inventory-name-input, .inventory-description-input').forEach((input) => {
        if (isLocked) {
            input.setAttribute('readonly', '');
        } else {
            input.removeAttribute('readonly');
        }
    });

    // ── Buffs section ──
    const buffsSection = document.querySelector('.custom-buffs-section');
    if (buffsSection) {
        buffsSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('[data-buff-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });

    // ── Add Buff action (lock-gated) ──
    const addBuffContainer = document.getElementById('add-buff-action-container');
    if (addBuffContainer) {
        addBuffContainer.style.display = isLocked ? 'none' : '';
        if (isLocked) {
            const w = document.getElementById('add-custom-buff-btn-wrapper');
            const f = document.getElementById('add-custom-buff-fields-wrapper');
            const s = document.getElementById('add-custom-buff-submit-btn-wrapper');
            const c = document.getElementById('close-custom-buff-btn-wrapper');
            if (w) w.style.display = '';
            if (f) f.style.display = 'none';
            if (s) s.style.display = 'none';
            if (c) c.style.display = 'none';
        }
    }

    // ── Tracker section ──
    const trackerSection = document.querySelector('.tracker-section');
    if (trackerSection) {
        trackerSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('[data-tracker-remove="true"], [data-tracker-entry-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });
    document.querySelectorAll('.tracker-name-input, .tracker-entry-name-input, .tracker-entry-value-input').forEach((input) => {
        if (isLocked) {
            input.setAttribute('readonly', '');
        } else {
            input.removeAttribute('readonly');
        }
    });
    document.querySelectorAll('.tracker-add-actions-row').forEach((row) => {
        row.style.display = isLocked ? 'none' : 'flex';
    });
    document.querySelectorAll('.tracker-add-entry-inline-btn').forEach((el) => {
        el.style.display = isLocked ? 'none' : 'flex';
    });
    // Hit Dice tracking is combat-tracking, not a build field — always usable
    // regardless of lock state (see bindHitDiceSteppers). It still gets
    // data-locked set purely so its help text hides on lock like every
    // other section's, via the generic [data-locked='true'] .section-help-text
    // rule — this does not gate any Hit Dice control.
    const hitDiceSection = document.querySelector('.hit-dice-section');
    if (hitDiceSection) {
        hitDiceSection.dataset.locked = String(isLocked);
    }
}

function bindGlobalLockToggle() {
    const lockBtn = document.getElementById('global-lock-toggle');
    if (!lockBtn || lockBtn.dataset.bound === 'true') {
        syncGlobalLockState();
        return;
    }
    lockBtn.dataset.bound = 'true';

    lockBtn.addEventListener('click', () => {
        const cookieKey = getGlobalLockCookieKey();
        const nowLocked = !getGlobalLockState();
        if (cookieKey) {
            setCookieValue(cookieKey, String(nowLocked), ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        }
        syncGlobalLockState();
    });

    lockBtn.addEventListener('keydown', (event) => {
        if (event.key === ' ' || event.key === 'Enter') {
            event.preventDefault();
            const cookieKey = getGlobalLockCookieKey();
            const nowLocked = !getGlobalLockState();
            if (cookieKey) {
                setCookieValue(cookieKey, String(nowLocked), ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncGlobalLockState();
        }
    });

    syncGlobalLockState();
}

function addBuffIndicator(el) {
    if (el && !el.querySelector('.buff-indicator')) {
        el.insertAdjacentHTML('beforeend', ' <span class="buff-indicator">*</span>');
    }
}

function clearBuffLabelDecorations() {
    document.querySelectorAll('.buff-indicator').forEach(el => el.remove());

    document.querySelectorAll('[data-buff-tooltip-applied="true"]').forEach((el) => {
        const hadOriginalTitle = el.dataset.hadOriginalTitle === 'true';
        const originalTitle = el.dataset.originalTitle || '';

        if (hadOriginalTitle) {
            el.setAttribute('title', originalTitle);
        } else {
            el.removeAttribute('title');
        }

        el.classList.remove('buff-tooltip-label');
        delete el.dataset.originalTitle;
        delete el.dataset.hadOriginalTitle;
        delete el.dataset.buffTooltipApplied;
    });
}

function formatBuffSourceLabel(source) {
    const rawName = String(source.buff_name || '').trim();
    const name = rawName || 'Unnamed Effect';
    const parsedValue = Number.parseInt(source.buff_value, 10);

    if (Number.isNaN(parsedValue)) {
        return name;
    }

    const valueLabel = parsedValue >= 0 ? `+${parsedValue}` : `${parsedValue}`;
    return `${name} (${valueLabel})`;
}

function setBuffTooltip(el, buffSources) {
    if (!el || !Array.isArray(buffSources) || buffSources.length === 0) {
        return;
    }

    if (el.dataset.buffTooltipApplied !== 'true') {
        el.dataset.originalTitle = el.getAttribute('title') || '';
        el.dataset.hadOriginalTitle = el.hasAttribute('title') ? 'true' : 'false';
    }

    const sourceLines = buffSources.map(formatBuffSourceLabel);
    const tooltip = sourceLines.length === 1
        ? `Affected by: ${sourceLines[0]}`
        : `Affected by:\n${sourceLines.map((line) => `- ${line}`).join('\n')}`;

    el.setAttribute('title', tooltip);
    el.classList.add('buff-tooltip-label');
    el.dataset.buffTooltipApplied = 'true';
}

function getBuffedLabelElement(table, stat) {
    const normalizedStat = String(stat);

    if (table === 'custom_stat') {
        const input = document.getElementById(`custom_stat-value-${normalizedStat}`);
        if (input && input.id) {
            return document.querySelector(`label[for="${input.id}"]`);
        }
        return null;
    }

    if (table === 'feat_and_trait') {
        const input = document.querySelector(`.feats-section .feat-name-input[data-feat-id="${normalizedStat}"]`);
        return input ? input.closest('.card-item-name-wrapper') : null;
    }

    if (table === 'inventory') {
        const input = document.getElementById(`inventory-name-${normalizedStat}`);
        return input ? input.closest('.card-item-name-wrapper') : null;
    }

    const key = `${table}-${normalizedStat}`;
    const input = document.querySelector(`input[name="${key}"]`);
    if (input && input.id) {
        return document.querySelector(`label[for="${input.id}"]`);
    }

    const displayDiv = document.getElementById(key);
    if (!displayDiv) {
        return null;
    }

    return displayDiv.closest('.abilities-section-secondary-field, .abilities-section-skills-item')?.querySelector('.abilities-section-display-label') || null;
}

function decorateBuffedLabels() {
    clearBuffLabelDecorations();

    const dataEl = document.getElementById('buff-fields-data');
    if (!dataEl) return;

    let buffFields;
    try {
        buffFields = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }

    if (!buffFields || !buffFields.length) return;

    const sourcesByField = new Map();

    buffFields.forEach((buffField) => {
        const table = String(buffField.table || '').trim();
        const stat = String(buffField.stat || '').trim();
        if (!table || !stat) {
            return;
        }

        const fieldKey = `${table}::${stat}`;
        if (!sourcesByField.has(fieldKey)) {
            sourcesByField.set(fieldKey, new Map());
        }

        const sourceMap = sourcesByField.get(fieldKey);
        const fallbackSourceKey = `${buffField.buff_name || ''}|${buffField.buff_value || ''}`;
        const sourceKey = buffField.buff_id != null ? String(buffField.buff_id) : fallbackSourceKey;
        if (!sourceMap.has(sourceKey)) {
            sourceMap.set(sourceKey, {
                buff_name: buffField.buff_name,
                buff_value: buffField.buff_value,
            });
        }
    });

    sourcesByField.forEach((sourceMap, fieldKey) => {
        const [table, stat] = fieldKey.split('::');
        const label = getBuffedLabelElement(table, stat);
        if (!label) {
            return;
        }

        addBuffIndicator(label);
        setBuffTooltip(label, Array.from(sourceMap.values()));
    });
}

function selectCustomBuffField() {
    const addCustomBuffBtn = document.getElementById('add-custom-buff-btn');
    const addCustomBuffBtnWrapper = document.getElementById('add-custom-buff-btn-wrapper');
    const addCustomBuffFieldsWrapper = document.getElementById('add-custom-buff-fields-wrapper');
    const addCustomBuffSubmitBtnWrapper = document.getElementById('add-custom-buff-submit-btn-wrapper');
    const closeCustomBuffBtnWrapper = document.getElementById('close-custom-buff-btn-wrapper');
    const closeCustomBuffFieldXBtn = document.getElementById('close-custom-buff-field-x-btn');
    const targetColumnsField = document.getElementById('add-custom-buff-target-columns-field');

    if (!addCustomBuffBtn || !addCustomBuffBtnWrapper || !addCustomBuffFieldsWrapper || !addCustomBuffSubmitBtnWrapper || !closeCustomBuffBtnWrapper || !closeCustomBuffFieldXBtn) {
        return;
    }

    const tableCheckboxes = document.querySelectorAll('.custom-buffs-table-checkbox');

    const updateTableStatGroups = () => {
        let hasSelectedTable = false;

        tableCheckboxes.forEach((tableCheckbox) => {
            const tableName = tableCheckbox.dataset.tableName;
            if (!tableName) {
                return;
            }

            const statGroup = document.querySelector(`.custom-buffs-table-stat-group[data-table-name="${tableName}"]`);
            if (!statGroup) {
                return;
            }

            if (tableCheckbox.checked) {
                hasSelectedTable = true;
                statGroup.classList.add('is-active');
                return;
            }

            statGroup.classList.remove('is-active');
            const groupCheckboxes = statGroup.querySelectorAll('.custom-buffs-stat-checkbox');
            groupCheckboxes.forEach((groupCheckbox) => {
                groupCheckbox.checked = false;
            });
        });

        if (targetColumnsField) {
            targetColumnsField.style.display = hasSelectedTable ? 'flex' : 'none';
        }
    };

    if (addCustomBuffBtn.dataset.bound !== 'true') {
        addCustomBuffBtn.addEventListener('click', () => {
            addCustomBuffBtnWrapper.style.display = 'none';
            addCustomBuffFieldsWrapper.style.display = 'flex';
            addCustomBuffSubmitBtnWrapper.style.display = 'flex';
            closeCustomBuffBtnWrapper.style.display = 'flex';
            updateTableStatGroups();
        });
        addCustomBuffBtn.dataset.bound = 'true';
    }

    if (closeCustomBuffFieldXBtn.dataset.bound !== 'true') {
        closeCustomBuffFieldXBtn.addEventListener('click', () => {
            addCustomBuffBtnWrapper.style.display = 'flex';
            addCustomBuffFieldsWrapper.style.display = 'none';
            addCustomBuffSubmitBtnWrapper.style.display = 'none';
            closeCustomBuffBtnWrapper.style.display = 'none';
        });
        closeCustomBuffFieldXBtn.dataset.bound = 'true';
    }

    tableCheckboxes.forEach((tableCheckbox) => {
        if (tableCheckbox.dataset.bound === 'true') {
            return;
        }

        tableCheckbox.addEventListener('change', () => {
            updateTableStatGroups();
        });

        tableCheckbox.dataset.bound = 'true';
    });

    updateTableStatGroups();
}

function bindAddClassButton() {
    const addClassBtn = document.getElementById('add-class-btn');
    const addClassBtnWrapper = document.getElementById('add-class-btn-wrapper');
    const addClassFieldDropdown = document.getElementById('add-class-field-dropdown');
    const addClassFieldLevel = document.getElementById('add-class-field-level');
    const addClassSubmitBtn = document.getElementById('add-class-submit-btn');
    const closeBtn = document.getElementById('close-add-class-btn');
    const closeBtnWrapper = document.getElementById('close-add-class-btn-wrapper');

    const showElement = (el) => { if (el) el.style.display = 'flex'; };
    const showBlockElement = (el) => { if (el) el.style.display = 'block'; };
    const hideElement = (el) => { if (el) el.style.display = 'none'; };

    const hideForm = () => {
        showElement(addClassBtnWrapper);
        hideElement(addClassFieldDropdown);
        hideElement(addClassFieldLevel);
        hideElement(addClassSubmitBtn);
        hideElement(closeBtnWrapper);
    };

    if (addClassBtn && addClassBtn.dataset.bound !== 'true') {
        addClassBtn.addEventListener('click', () => {
            hideElement(addClassBtnWrapper);
            showBlockElement(addClassFieldDropdown);
            showElement(addClassFieldLevel);
            showElement(addClassSubmitBtn);
            showElement(closeBtnWrapper);
        });
        addClassBtn.dataset.bound = 'true';
    }

    if (closeBtn && closeBtn.dataset.bound !== 'true') {
        closeBtn.addEventListener('click', hideForm);
        closeBtn.dataset.bound = 'true';
    }
}

function bindAddStatButton() {
    const addCustomStatBtn = document.getElementById('add-custom-stat-btn');
    const addCustomStatBtnWrapper = document.getElementById('add-custom-stat-btn-wrapper');
    const addCustomStatFieldName = document.getElementById('add-custom-stat-field-name');
    const addCustomStatFieldValue = document.getElementById('add-custom-stat-field-value');
    const addCustomStatSubmitBtnWrapper = document.getElementById('add-custom-stat-submit-btn-wrapper');
    const closeBtn = document.getElementById('close-add-stat-btn');
    const closeBtnWrapper = document.getElementById('close-add-stat-btn-wrapper');

    const showElement = (el) => { if (el) el.style.display = 'flex'; };
    const hideElement = (el) => { if (el) el.style.display = 'none'; };

    const hideForm = () => {
        showElement(addCustomStatBtnWrapper);
        hideElement(addCustomStatFieldName);
        hideElement(addCustomStatFieldValue);
        hideElement(addCustomStatSubmitBtnWrapper);
        hideElement(closeBtnWrapper);
    };

    if (addCustomStatBtn && addCustomStatBtn.dataset.bound !== 'true') {
        addCustomStatBtn.addEventListener('click', () => {
            hideElement(addCustomStatBtnWrapper);
            showElement(addCustomStatFieldName);
            showElement(addCustomStatFieldValue);
            showElement(addCustomStatSubmitBtnWrapper);
            showElement(closeBtnWrapper);
        });
        addCustomStatBtn.dataset.bound = 'true';
    }

    if (closeBtn && closeBtn.dataset.bound !== 'true') {
        closeBtn.addEventListener('click', hideForm);
        closeBtn.dataset.bound = 'true';
    }
}

function selectFeatField() {
    const addFeatBtn = document.getElementById('add-feat-btn');
    const addFeatBtnWrapper = document.getElementById('add-feat-btn-wrapper');
    const addFeatFieldName = document.getElementById('add-feat-field-name');
    const addFeatFieldDescription = document.getElementById('add-feat-field-description');
    const addFeatSubmitBtnWrapper = document.getElementById('add-feat-submit-btn-wrapper');
    const closeFeatBtnWrapper = document.getElementById('close-feat-btn-wrapper');
    const closeFeatFieldXBtn = document.getElementById('close-feat-field-x-btn');

    if (!addFeatBtn || !addFeatBtnWrapper || !addFeatFieldName || !addFeatFieldDescription || !addFeatSubmitBtnWrapper || !closeFeatBtnWrapper || !closeFeatFieldXBtn) {
        return;
    }

    if (addFeatBtn.dataset.bound !== 'true') {
        addFeatBtn.addEventListener('click', () => {
            addFeatBtnWrapper.style.display = 'none';
            addFeatFieldName.style.display = 'flex';
            addFeatFieldDescription.style.display = 'flex';
            addFeatSubmitBtnWrapper.style.display = 'flex';
            closeFeatBtnWrapper.style.display = 'flex';

            const addDescriptionField = addFeatFieldDescription.querySelector('.card-item-description-input');
            if (addDescriptionField) {
                if (addDescriptionField.dataset.autoresizeBound !== 'true') {
                    addDescriptionField.addEventListener('input', () => {
                        resizeFeatDescriptionField(addDescriptionField);
                    });
                    addDescriptionField.dataset.autoresizeBound = 'true';
                }
                addDescriptionField.style.height = '';
                resizeFeatDescriptionField(addDescriptionField);
            }
        });
        addFeatBtn.dataset.bound = 'true';
    }

    if (closeFeatFieldXBtn.dataset.bound !== 'true') {
        closeFeatFieldXBtn.addEventListener('click', () => {
            addFeatBtnWrapper.style.display = 'flex';
            addFeatFieldName.style.display = 'none';
            addFeatFieldDescription.style.display = 'none';
            addFeatSubmitBtnWrapper.style.display = 'none';
            closeFeatBtnWrapper.style.display = 'none';
        });
        closeFeatFieldXBtn.dataset.bound = 'true';
    }
}

function selectInventoryField() {
    const addInventoryBtn = document.getElementById('add-inventory-btn');
    const addInventoryBtnWrapper = document.getElementById('add-inventory-btn-wrapper');
    const addInventoryFieldName = document.getElementById('add-inventory-field-name');
    const addInventoryFieldQuantity = document.getElementById('add-inventory-field-quantity');
    const addInventoryFieldDescription = document.getElementById('add-inventory-field-description');
    const addInventorySubmitBtnWrapper = document.getElementById('add-inventory-submit-btn-wrapper');
    const closeInventoryBtnWrapper = document.getElementById('close-inventory-btn-wrapper');
    const closeInventoryFieldXBtn = document.getElementById('close-inventory-field-x-btn');

    if (!addInventoryBtn || !addInventoryBtnWrapper || !addInventoryFieldName || !addInventoryFieldQuantity || !addInventoryFieldDescription || !addInventorySubmitBtnWrapper || !closeInventoryBtnWrapper || !closeInventoryFieldXBtn) {
        return;
    }

    if (addInventoryBtn.dataset.bound !== 'true') {
        addInventoryBtn.addEventListener('click', () => {
            addInventoryBtnWrapper.style.display = 'none';
            addInventoryFieldName.style.display = 'flex';
            addInventoryFieldQuantity.style.display = 'flex';
            addInventoryFieldDescription.style.display = 'flex';
            addInventorySubmitBtnWrapper.style.display = 'flex';
            closeInventoryBtnWrapper.style.display = 'flex';

            const addDescriptionField = addInventoryFieldDescription.querySelector('.card-item-description-input');
            if (addDescriptionField) {
                addDescriptionField.style.height = '';
                resizeInventoryDescriptionField(addDescriptionField);
            }
        });
        addInventoryBtn.dataset.bound = 'true';
    }

    if (closeInventoryFieldXBtn.dataset.bound !== 'true') {
        closeInventoryFieldXBtn.addEventListener('click', () => {
            addInventoryBtnWrapper.style.display = 'flex';
            addInventoryFieldName.style.display = 'none';
            addInventoryFieldQuantity.style.display = 'none';
            addInventoryFieldDescription.style.display = 'none';
            addInventorySubmitBtnWrapper.style.display = 'none';
            closeInventoryBtnWrapper.style.display = 'none';
        });
        closeInventoryFieldXBtn.dataset.bound = 'true';
    }
}

function resizeFeatDescriptionField(field) {
    if (!field) {
        return;
    }

    // Collapse to CSS min-height so scrollHeight reflects actual content
    field.style.height = '0';
    field.style.height = `${field.scrollHeight}px`;
}

function resizeInventoryDescriptionField(field) {
    if (!field) {
        return;
    }

    // Collapse to CSS min-height so scrollHeight reflects actual content
    field.style.height = '0';
    field.style.height = `${field.scrollHeight}px`;
}

const inventoryAutoSave = createDebouncedSaver();

function saveInventoryRow(inventoryId) {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const row = document.getElementById(`inventory-row-${inventoryId}`);
    if (!row) {
        return;
    }
    const nameInput = row.querySelector('.inventory-name-input');
    const descInput = row.querySelector('.inventory-description-input');
    const qtyInput = row.querySelector('.inventory-quantity-input');
    if (!nameInput) {
        return;
    }

    htmx.ajax('POST', `/characters/${characterId}/inventory/${inventoryId}/update`, {
        source: nameInput,
        target: `#inventory-row-${inventoryId}`,
        swap: 'outerHTML',
        values: {
            [`inventory-name-${inventoryId}`]: nameInput.value,
            [`inventory-description-${inventoryId}`]: descInput ? descInput.value : '',
            [`inventory-quantity-${inventoryId}`]: qtyInput ? qtyInput.value : '',
        }
    });
}

function bindInventoryAutoSave() {
    const inventorySection = document.querySelector('.inventory-section');
    if (!inventorySection) {
        return;
    }

    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return;
    }

    const rows = inventorySection.querySelectorAll('.card-item-saved-row');

    rows.forEach((row) => {
        const nameInput = row.querySelector('.inventory-name-input');
        const descInput = row.querySelector('.inventory-description-input');
        if (!nameInput) return;

        const inventoryId = nameInput.dataset.inventoryId;
        if (!inventoryId) return;

        const triggerAutoSave = () => inventoryAutoSave.schedule(inventoryId, () => saveInventoryRow(inventoryId));

        [nameInput, descInput].forEach((input) => {
            if (!input || input.dataset.autoSaveBound === 'true') return;
            input.dataset.autoSaveBound = 'true';
            input.addEventListener('input', triggerAutoSave);
        });

        row.querySelectorAll('[data-inventory-step]').forEach((button) => {
            if (button.dataset.stepBound === 'true') return;
            button.dataset.stepBound = 'true';
            button.addEventListener('click', () => {
                const qtyInput = row.querySelector('.inventory-quantity-input');
                if (!qtyInput) return;

                const step = parseInt(button.dataset.inventoryStep, 10) || 0;
                const current = parseInt(qtyInput.value, 10) || 0;
                const next = Math.max(0, current + step);
                qtyInput.value = next;

                // Keep the decrease button's lock/trash-icon state in sync without a server round trip.
                const decreaseBtn = row.querySelector('[data-inventory-remove="true"]');
                if (decreaseBtn) {
                    decreaseBtn.dataset.itemQuantity = String(next);
                }
                syncGlobalLockState();

                if (next <= 0) {
                    // Reaching zero deletes the item — destructive, so save immediately rather than waiting out the debounce.
                    inventoryAutoSave.cancel(inventoryId);
                    saveInventoryRow(inventoryId);
                } else {
                    inventoryAutoSave.schedule(inventoryId, () => saveInventoryRow(inventoryId));
                }
            });
        });
    });
}

function bindCurrentHpCalculation() {
    const tempHpField = document.getElementById('character-temporary_hit_points');
    const currentHpField = document.getElementById('character-current_health_points');
    const decreaseCurrentHpBtn = document.getElementById('decrease-current-hp-btn');
    const increaseCurrentHpBtn = document.getElementById('increase-current-hp-btn');
    const damageHealthField = document.getElementById('damage-health-calc');
    const currentHpMaxSuffix = document.getElementById('current-hp-max-suffix');

    if (!tempHpField || !currentHpField) {
        return;
    }

    const getCharacterId = () => {
        const characterIdField = document.getElementById('character-id');
        return characterIdField ? String(characterIdField.value || '').trim() : '';
    };

    const getCurrentHpCookieKey = () => {
        const characterId = getCharacterId();
        return characterId ? `current_hp_${characterId}` : null;
    };

    const saveCurrentHpToCookie = () => {
        const cookieKey = getCurrentHpCookieKey();
        if (cookieKey && currentHpField.value !== '') {
            setCookieValue(cookieKey, currentHpField.value, CURRENT_HP_COOKIE_MAX_AGE_SECONDS);
        }
    };

    // Temp HP is cookie-only now too — no DB field, never autosaved.
    const getTempHpCookieKey = () => {
        const characterId = getCharacterId();
        return characterId ? `temp_hp_${characterId}` : null;
    };

    const saveTempHpToCookie = () => {
        const cookieKey = getTempHpCookieKey();
        if (cookieKey) {
            setCookieValue(cookieKey, tempHpField.value, CURRENT_HP_COOKIE_MAX_AGE_SECONDS);
        }
    };

    const clearCurrentHpCookie = () => {
        const cookieKey = getCurrentHpCookieKey();
        if (!cookieKey) {
            return;
        }
        const encodedName = encodeURIComponent(cookieKey);
        document.cookie = `${encodedName}=; path=/; max-age=0; SameSite=Lax`;
    };

    const parseNumberOrZero = (value) => {
        if (value === '--' || value === '') return 0;
        const parsed = Number.parseInt(value, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const parseTempHp = (value) => {
        return Math.max(0, parseNumberOrZero(value));
    };

    const isEmptyLikeValue = (value) => {
        const normalized = String(value ?? '').trim();
        return normalized === '' || normalized === '--';
    };

    const displayTempHp = (numericValue) => {
        const normalizedTempHp = Math.max(0, parseNumberOrZero(numericValue));
        tempHpField.value = normalizedTempHp > 0 ? normalizedTempHp : '';
    };

    // Health Points now lives in the Character Info section — a container
    // that can re-render independently of this one (the Trackers tab). Look
    // it up fresh every time instead of closing over a single node, so this
    // logic keeps working correctly even after that section swaps in a new
    // node out from under an already-bound Temp HP/Current HP closure.
    const getHealthPointsField = () => document.getElementById('character-health_points');

    const getHealthPoints = () => {
        const healthPointsField = getHealthPointsField();
        return healthPointsField ? Math.max(0, parseNumberOrZero(healthPointsField.value)) : 0;
    };

    const getTempHp = () => {
        return parseTempHp(tempHpField.value);
    };

    const getMaxCurrentHp = () => {
        return Math.max(0, getHealthPoints() + getTempHp());
    };

    const syncCombatStateColours = () => {
        applyCombatStateColours({ healthPointsField: getHealthPointsField(), tempHpField, currentHpField });
    };

    const syncCurrentHpVisibility = () => {
        const healthPointsField = getHealthPointsField();
        if (!healthPointsField) return;
        const isEmpty = isEmptyLikeValue(healthPointsField.value);

        const currentHpWrapper = currentHpField.closest('.combat-section-col-two-field');
        if (currentHpWrapper) currentHpWrapper.classList.toggle('hp-not-set', isEmpty);

        // Only these two specific fields — not the whole column, since Hit
        // Dice fields now share it too and must stay visible regardless.
        const tempHpWrapper = tempHpField.closest('.combat-section-col-one-field');
        if (tempHpWrapper) tempHpWrapper.classList.toggle('hp-not-set', isEmpty);

        const damageHealthWrapper = damageHealthField ? damageHealthField.closest('.combat-section-col-one-field') : null;
        if (damageHealthWrapper) damageHealthWrapper.classList.toggle('hp-not-set', isEmpty);
    };

    // Static reference to the character's Health Points total — only ever
    // changes when the Health Points field itself changes, never when Temp
    // HP or Current HP fluctuate.
    const syncMaxHpSuffix = () => {
        if (!currentHpMaxSuffix) return;
        const healthPointsField = getHealthPointsField();
        const isSet = healthPointsField && !isEmptyLikeValue(healthPointsField.value);
        currentHpMaxSuffix.textContent = isSet ? `/${healthPointsField.value}` : '/--';
    };

    // Restore Temp HP from its cookie on first bind, before the initial max
    // baseline below is computed, so it correctly includes the restored value.
    if (currentHpField.dataset.hpCalcBound !== 'true') {
        const tempHpCookieKey = getTempHpCookieKey();
        const savedTempHp = tempHpCookieKey ? getCookieValue(tempHpCookieKey) : null;
        if (savedTempHp !== null && savedTempHp !== '') {
            tempHpField.value = savedTempHp;
        }
    }

    let previousMaxCurrentHp = getMaxCurrentHp();

    const adjustCurrentHp = (delta) => {
        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxCurrentHp = getMaxCurrentHp();

        if (delta > 0) {
            currentHpField.value = Math.min(maxCurrentHp, currentHp + delta);
            saveCurrentHpToCookie();
            syncCombatStateColours();
            return;
        }

        if (delta < 0) {
            const damage = Math.abs(delta);
            if (currentHp <= 0) {
                currentHpField.value = 0;
                saveCurrentHpToCookie();
                syncCombatStateColours();
                return;
            }

            // Temp HP absorbs damage first, up to however much it has — not a
            // flat 1 per click, so this stays correct for arbitrary amounts
            // (the Damage/Health calculator), not just the ±1 buttons. This is
            // bookkeeping only — it doesn't dispatch a synthetic input event,
            // since that would trigger a nested calculateCurrentHp() recalculation
            // whose result the line below would then stomp with a stale currentHp.
            const tempHp = getTempHp();
            const absorbed = Math.min(tempHp, damage);
            if (absorbed > 0) {
                displayTempHp(tempHp - absorbed);
                saveTempHpToCookie();
            }

            currentHpField.value = Math.max(0, currentHp - damage);
            saveCurrentHpToCookie();
            syncCombatStateColours();
        }
    };

    const calculateCurrentHp = () => {
        syncCurrentHpVisibility();
        saveTempHpToCookie();
        syncMaxHpSuffix();

        const healthPointsField = getHealthPointsField();
        const healthPointsEmpty = !healthPointsField || isEmptyLikeValue(healthPointsField.value);

        if (healthPointsEmpty && isEmptyLikeValue(tempHpField.value)) {
            currentHpField.value = '';
            previousMaxCurrentHp = 0;
            clearCurrentHpCookie();
            syncCombatStateColours();
            return;
        }

        const maxCurrentHp = getMaxCurrentHp();

        if (currentHpField.value === '') {
            currentHpField.value = maxCurrentHp;
            previousMaxCurrentHp = maxCurrentHp;
            saveCurrentHpToCookie();
            syncCombatStateColours();
            return;
        }

        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxDelta = maxCurrentHp - previousMaxCurrentHp;
        const adjustedCurrentHp = currentHp + maxDelta;

        currentHpField.value = Math.min(maxCurrentHp, Math.max(0, adjustedCurrentHp));
        previousMaxCurrentHp = maxCurrentHp;
        saveCurrentHpToCookie();
        syncCombatStateColours();
    };

    // ── Combat-section side (Temp HP, Current HP, buttons, Damage/Health
    // calc) — these all live together and swap together, so one shared guard
    // covers this half. ──
    if (currentHpField.dataset.hpCalcBound !== 'true') {
        currentHpField.dataset.hpCalcBound = 'true';

        // Restore from cookie on initial bind
        const cookieKey = getCurrentHpCookieKey();
        const savedHp = cookieKey ? getCookieValue(cookieKey) : null;
        if (savedHp !== null && savedHp !== '') {
            const maxCurrentHp = getMaxCurrentHp();
            const restoredHp = Math.min(maxCurrentHp, Math.max(0, parseNumberOrZero(savedHp)));
            currentHpField.value = restoredHp;
        }

        tempHpField.addEventListener('input', calculateCurrentHp);

        tempHpField.addEventListener('blur', () => {
            displayTempHp(parseTempHp(tempHpField.value));
            calculateCurrentHp();
        });

        // Steps by 1 by default; if an amount is typed into the Damage/Health
        // calculator first, these same buttons step by that amount instead
        // (and clear it afterward) — one reusable control rather than two.
        const stepCurrentHp = (sign) => {
            const typedAmount = damageHealthField ? parseInt(damageHealthField.value, 10) : NaN;
            const hasTypedAmount = Number.isFinite(typedAmount) && typedAmount > 0;
            adjustCurrentHp(sign * (hasTypedAmount ? typedAmount : 1));
            if (hasTypedAmount) {
                damageHealthField.value = '';
            }
        };

        if (decreaseCurrentHpBtn) {
            decreaseCurrentHpBtn.addEventListener('click', () => stepCurrentHp(-1));
        }

        if (increaseCurrentHpBtn) {
            increaseCurrentHpBtn.addEventListener('click', () => stepCurrentHp(1));
        }

        currentHpField.addEventListener('input', () => {
            const currentHp = parseNumberOrZero(currentHpField.value);
            const maxCurrentHp = getMaxCurrentHp();
            currentHpField.value = Math.min(maxCurrentHp, Math.max(0, currentHp));
            saveCurrentHpToCookie();
            syncCombatStateColours();
        });
    }

    // ── Health Points side — independent guard, since it now lives in a
    // different container (Character Info) that can swap on its own. ──
    const healthPointsField = getHealthPointsField();
    if (healthPointsField && healthPointsField.dataset.hpCalcBound !== 'true') {
        healthPointsField.dataset.hpCalcBound = 'true';
        healthPointsField.addEventListener('input', calculateCurrentHp);
    }

    calculateCurrentHp();
}

function getCharacterProficiencyBonus() {
    const field = document.getElementById('character-proficiency');
    const parsed = field ? parseInt(field.value, 10) : NaN;
    return Number.isFinite(parsed) ? parsed : 0;
}

function getAbilityBuffDelta(table, stat) {
    const dataEl = document.getElementById('buff-fields-data');
    if (!dataEl) return 0;
    let buffFields;
    try {
        buffFields = JSON.parse(dataEl.textContent);
    } catch (e) {
        return 0;
    }
    if (!Array.isArray(buffFields)) return 0;
    return buffFields.reduce((total, field) => {
        if (field.table !== table || field.stat !== stat) return total;
        const value = Number.parseInt(field.buff_value, 10);
        return Number.isNaN(value) ? total : total + value;
    }, 0);
}

function formatSignedNumber(value) {
    return value > 0 ? `+${value}` : String(value);
}

function recomputeAbilityRowDisplay(row) {
    const abilityName = row.id.replace('ability-row-', '');
    if (!abilityName) return;
    const skillsTable = `${abilityName}_skills`;

    const valueInput = document.getElementById(`${abilityName}-value`);
    const rawValue = valueInput ? parseInt(valueInput.value, 10) : NaN;
    const abilityValue = Number.isFinite(rawValue) ? Math.min(30, Math.max(1, rawValue)) : 10;
    const modifier = Math.floor((abilityValue - 10) / 2);

    const modifierDisplay = document.getElementById(`${abilityName}-modifier`);
    if (modifierDisplay) {
        modifierDisplay.textContent = formatSignedNumber(modifier + getAbilityBuffDelta(abilityName, 'modifier'));
    }

    const proficiencyBonus = getCharacterProficiencyBonus();

    const savingCheckbox = document.getElementById(`${abilityName}-proficient`);
    const savingDisplay = document.getElementById(`${abilityName}_skills-saving_throw`);
    if (savingDisplay) {
        const savingBuff = getAbilityBuffDelta(skillsTable, 'saving_throw');
        savingDisplay.textContent = formatSignedNumber(modifier + (savingCheckbox && savingCheckbox.checked ? proficiencyBonus : 0) + savingBuff);
    }

    row.querySelectorAll('.abilities-section-skills-item .hidden-proficiency-checkbox').forEach((checkbox) => {
        const item = checkbox.closest('.abilities-section-skills-item');
        const valueDisplay = item ? item.querySelector('.abilities-section-display-value') : null;
        if (!valueDisplay) return;
        const skillName = checkbox.id.replace(`${skillsTable}-`, '').replace('_proficient', '');
        const skillBuff = getAbilityBuffDelta(skillsTable, skillName);
        valueDisplay.textContent = formatSignedNumber(modifier + (checkbox.checked ? proficiencyBonus : 0) + skillBuff);
    });

    recomputePassiveStats();
}

function recomputePassiveStats() {
    document.querySelectorAll('.character-info-passive-value[data-skill-source]').forEach((el) => {
        const sourceId = el.dataset.skillSource;
        const source = sourceId ? document.getElementById(sourceId) : null;
        const rawValue = source ? parseInt(source.textContent, 10) : NaN;
        const skillValue = Number.isFinite(rawValue) ? rawValue : 0;
        el.textContent = String(10 + skillValue);
    });
}

const abilityAutoSave = createDebouncedSaver();

function saveAbilityRow(abilityName) {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) return;

    const row = document.getElementById(`ability-row-${abilityName}`);
    if (!row) return;
    const valueInput = document.getElementById(`${abilityName}-value`);
    if (!valueInput) return;

    const values = { [`${abilityName}-value`]: valueInput.value };
    row.querySelectorAll('.hidden-proficiency-checkbox').forEach((checkbox) => {
        if (checkbox.checked && checkbox.name) values[checkbox.name] = '1';
    });

    htmx.ajax('POST', `/characters/${characterId}/abilities-skills/${abilityName}/update`, {
        target: `#ability-row-${abilityName}`,
        swap: 'outerHTML',
        values,
    });
}

function bindAbilityAutoSave() {
    const abilitiesSection = document.querySelector('.abilities-section');
    if (!abilitiesSection) return;
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) return;

    abilitiesSection.querySelectorAll('.abilities-section-row').forEach((row) => {
        const abilityName = row.id.replace('ability-row-', '');
        if (!abilityName) return;

        const valueInput = row.querySelector('.abilities-section-name-input');
        if (valueInput && valueInput.dataset.autoSaveBound !== 'true') {
            valueInput.dataset.autoSaveBound = 'true';
            valueInput.addEventListener('input', () => {
                recomputeAbilityRowDisplay(row);
                abilityAutoSave.schedule(`${abilityName}-value`, () => saveAbilityRow(abilityName));
            });
        }

        row.querySelectorAll('.hidden-proficiency-checkbox').forEach((checkbox) => {
            if (checkbox.dataset.autoSaveBound === 'true') return;
            checkbox.dataset.autoSaveBound = 'true';
            checkbox.addEventListener('change', () => {
                recomputeAbilityRowDisplay(row);
                abilityAutoSave.schedule(`${abilityName}-toggles`, () => saveAbilityRow(abilityName));
            });
        });
    });
}

function bindAbilityStepButtons() {
    const abilitiesSection = document.querySelector('.abilities-section');
    if (!abilitiesSection || abilitiesSection.dataset.stepBound === 'true') return;
    abilitiesSection.dataset.stepBound = 'true';

    abilitiesSection.addEventListener('click', (event) => {
        const button = event.target.closest('.abilities-section-step-btn');
        if (!button || button.disabled) return;

        const abilityName = button.dataset.abilityName;
        const step = parseInt(button.dataset.abilityStep, 10) || 0;
        const valueInput = abilityName ? document.getElementById(`${abilityName}-value`) : null;
        if (!valueInput) return;

        const current = parseInt(valueInput.value, 10) || 0;
        const next = Math.min(30, Math.max(1, current + step));
        if (next === current) return;

        valueInput.value = next;
        valueInput.dispatchEvent(new Event('input', { bubbles: true }));
    });
}

// An ability row has two independently-debounced groups sharing one save call:
// the score field (continuous typing) and the proficiency toggles (discrete
// clicks, all coalesced together since the backend always saves the whole
// row's checkbox state in one request regardless of which toggle changed).
// Flushing a row means flushing both groups, but only saving once if both
// happened to be pending together.
function flushAbilityRow(abilityName) {
    let shouldSave = false;
    if (abilityAutoSave.hasPending(`${abilityName}-value`)) {
        abilityAutoSave.cancel(`${abilityName}-value`);
        shouldSave = true;
    }
    if (abilityAutoSave.hasPending(`${abilityName}-toggles`)) {
        abilityAutoSave.cancel(`${abilityName}-toggles`);
        shouldSave = true;
    }
    if (shouldSave) saveAbilityRow(abilityName);
}

function bindAbilitiesContainerSettle() {
    const container = document.getElementById('abilities-section-container');
    if (!container || container.dataset.settleBound === 'true') {
        return;
    }
    container.dataset.settleBound = 'true';

    container.addEventListener('htmx:afterSettle', () => {
        setTimeout(() => {
            bindAbilityAutoSave();
            bindProficiencyToggles();
            syncGlobalLockState();
            decorateBuffedLabels();
        }, 0);
    });

    container.addEventListener('focusout', (event) => {
        const row = event.target.closest('.abilities-section-row');
        if (!row) return;
        const stillInRow = event.relatedTarget && row.contains(event.relatedTarget);
        if (stillInRow) return;
        const abilityName = row.id.replace('ability-row-', '');
        if (abilityName) flushAbilityRow(abilityName);
    });

    container.addEventListener('htmx:beforeSwap', (event) => {
        if (event.detail.target !== container) return;
        flushAllPendingAbilities();
    });
}

function flushAllPendingAbilities() {
    const container = document.getElementById('abilities-section-container');
    if (!container) return;
    container.querySelectorAll('.abilities-section-row').forEach((row) => {
        const abilityName = row.id.replace('ability-row-', '');
        if (abilityName) flushAbilityRow(abilityName);
    });
}

function bindProficiencyToggles() {
    const proficiencyToggleItems = document.querySelectorAll('.proficiency-toggle-item');

    proficiencyToggleItems.forEach((item) => {
        if (item.dataset.bound === 'true') return;
        item.dataset.bound = 'true';

        const checkboxId = item.dataset.checkboxId;
        if (!checkboxId) {
            return;
        }

        const checkbox = document.getElementById(checkboxId);
        if (!checkbox) {
            return;
        }

        const syncVisualState = () => {
            item.classList.toggle('proficient-active', checkbox.checked);
            item.setAttribute('aria-pressed', checkbox.checked ? 'true' : 'false');
        };

        const toggleCheckbox = () => {
            const wasChecked = checkbox.checked;
            checkbox.checked = !checkbox.checked;
            syncVisualState();
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));

            if (wasChecked && !checkbox.checked) {
                item.classList.add('toggle-border-suppressed');
                window.setTimeout(() => {
                    item.classList.remove('toggle-border-suppressed');
                }, 180);
            }
        };

        item.addEventListener('click', () => {
            const section = item.closest('.abilities-section');
            if (section && section.dataset.locked === 'true') {
                return;
            }

            toggleCheckbox();
        });

        item.addEventListener('keydown', (event) => {
            const section = item.closest('.abilities-section');
            if (section && section.dataset.locked === 'true') {
                return;
            }

            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                toggleCheckbox();
            }
        });

        syncVisualState();
    });
}

function bindFeatDescriptionDisplayAutoHeight() {
    const descriptionFields = document.querySelectorAll('.feats-section .card-item-saved-row .card-item-description-input');

    descriptionFields.forEach((field) => {
        // Defer initial resize so the browser has laid out the swapped content
        setTimeout(() => resizeFeatDescriptionField(field), 0);

        if (field.dataset.autoresizeBound !== 'true') {
            field.addEventListener('input', () => {
                resizeFeatDescriptionField(field);
            });
            field.dataset.autoresizeBound = 'true';
        }
    });

    // Also handle the add-form textarea
    const addDescriptionField = document.getElementById('feat_and_trait-description') || document.querySelector('.feats-section .card-item-add-row .card-item-description-input');
    if (addDescriptionField && addDescriptionField.dataset.autoresizeBound !== 'true') {
        addDescriptionField.addEventListener('input', () => {
            resizeFeatDescriptionField(addDescriptionField);
        });
        addDescriptionField.dataset.autoresizeBound = 'true';
    }

    if (!featDescriptionResizeWindowBound) {
        window.addEventListener('resize', () => {
            const activeDescriptionFields = document.querySelectorAll('.feats-section .card-item-description-input');
            activeDescriptionFields.forEach((field) => {
                if (field.offsetParent === null) {
                    return;
                }

                resizeFeatDescriptionField(field);
            });
        });
        featDescriptionResizeWindowBound = true;
    }
}

function bindInventoryDescriptionDisplayAutoHeight() {
    const descriptionFields = document.querySelectorAll('.inventory-section .card-item-saved-row .card-item-description-input');

    descriptionFields.forEach((field) => {
        // Defer initial resize so the browser has laid out the swapped content
        setTimeout(() => resizeInventoryDescriptionField(field), 0);

        if (field.dataset.autoresizeBound !== 'true') {
            field.addEventListener('input', () => {
                resizeInventoryDescriptionField(field);
            });
            field.dataset.autoresizeBound = 'true';
        }
    });

    // Also handle the add-form textarea
    const addDescriptionField = document.querySelector('.inventory-section .card-item-add-row .card-item-description-input');
    if (addDescriptionField && addDescriptionField.dataset.autoresizeBound !== 'true') {
        addDescriptionField.addEventListener('input', () => {
            resizeInventoryDescriptionField(addDescriptionField);
        });
        addDescriptionField.dataset.autoresizeBound = 'true';
    }

    if (!inventoryDescriptionResizeWindowBound) {
        window.addEventListener('resize', () => {
            const activeDescriptionFields = document.querySelectorAll('.inventory-section .card-item-description-input');
            activeDescriptionFields.forEach((field) => {
                if (field.offsetParent === null) {
                    return;
                }

                resizeInventoryDescriptionField(field);
            });
        });
        inventoryDescriptionResizeWindowBound = true;
    }
}

// ── Tracker toggles ──────────────────────────────────────────────────────────

function getTrackerToggleCookieKey(characterId, trackerId, entryId) {
    return `tracker_state_${characterId}_${trackerId}_${entryId}`;
}

function bindTrackerToggles() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';

    document.querySelectorAll('.tracker-toggle').forEach((toggle) => {
        if (toggle.dataset.bound === 'true') return;
        toggle.dataset.bound = 'true';

        const trackerId = toggle.dataset.trackerId;
        const entryId = toggle.dataset.entryId;
        const index = parseInt(toggle.dataset.index, 10);

        // Restore state from cookie
        if (characterId && trackerId && entryId) {
            const cookieKey = getTrackerToggleCookieKey(characterId, trackerId, entryId);
            const raw = getCookieValue(cookieKey);
            if (raw) {
                try {
                    const checkedIndices = JSON.parse(raw);
                    if (Array.isArray(checkedIndices) && checkedIndices.includes(index)) {
                        toggle.classList.add('checked');
                        toggle.setAttribute('aria-checked', 'true');
                    }
                } catch (_) { /* ignore */ }
            }
        }

        const saveState = () => {
            if (!characterId || !trackerId || !entryId) return;
            const cookieKey = getTrackerToggleCookieKey(characterId, trackerId, entryId);
            const allToggles = document.querySelectorAll(
                `.tracker-toggle[data-tracker-id="${trackerId}"][data-entry-id="${entryId}"]`
            );
            const checkedIndices = [];
            allToggles.forEach((t) => {
                if (t.classList.contains('checked')) {
                    checkedIndices.push(parseInt(t.dataset.index, 10));
                }
            });
            setCookieValue(cookieKey, JSON.stringify(checkedIndices), ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        };

        const doToggle = () => {
            const isChecked = toggle.classList.contains('checked');
            toggle.classList.toggle('checked', !isChecked);
            toggle.setAttribute('aria-checked', String(!isChecked));
            saveState();
        };

        toggle.addEventListener('click', doToggle);
        toggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                doToggle();
            }
        });
    });
}

// ── Hit Dice (auto per-class counter) ───────────────────────────────────────
// Count and die size are server-computed (level + CLASS_HIT_DIE_MAPPING); only
// the "used" count is tracked here, client-side only, the same way tracker
// toggles are — no DB field for it.

function getHitDiceUsedCookieKey(characterId, classId) {
    return `hit_dice_used_${characterId}_${classId}`;
}

function getHitDiceCharacterId() {
    const characterIdField = document.getElementById('character-id');
    return characterIdField ? String(characterIdField.value || '').trim() : '';
}

function renderHitDiceRemaining(item) {
    const classId = item.dataset.classId;
    const max = parseInt(item.dataset.hitDiceMax, 10) || 0;
    const remainingEl = document.getElementById(`hit-dice-remaining-${classId}`);
    if (!remainingEl) return;

    const characterId = getHitDiceCharacterId();
    if (!characterId || !classId) {
        remainingEl.textContent = max;
        return;
    }

    const used = Math.min(max, Math.max(0, parseInt(getCookieValue(getHitDiceUsedCookieKey(characterId, classId)), 10) || 0));
    remainingEl.textContent = Math.max(0, max - used);
}

function adjustHitDiceUsed(item, usedDelta) {
    const classId = item.dataset.classId;
    const max = parseInt(item.dataset.hitDiceMax, 10) || 0;
    const characterId = getHitDiceCharacterId();
    if (!characterId || !classId) return;

    const cookieKey = getHitDiceUsedCookieKey(characterId, classId);
    const current = Math.min(max, Math.max(0, parseInt(getCookieValue(cookieKey), 10) || 0));
    const next = Math.min(max, Math.max(0, current + usedDelta));
    setCookieValue(cookieKey, String(next), ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
    renderHitDiceRemaining(item);
}

function bindHitDiceSteppers() {
    document.querySelectorAll('.hit-dice-tracker-item').forEach((item) => {
        renderHitDiceRemaining(item);

        item.querySelectorAll('.hit-dice-step-btn').forEach((button) => {
            if (button.dataset.bound === 'true') return;
            button.dataset.bound = 'true';
            button.addEventListener('click', () => {
                // The "-" button spends a die (remaining down, used up); "+" regains one.
                const step = parseInt(button.dataset.hitDiceStep, 10) || 0;
                adjustHitDiceUsed(item, -step);
            });
        });
    });
}

function performFullRest() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';

    // 1. Uncheck all tracker toggles and clear their cookies
    document.querySelectorAll('.tracker-toggle.checked').forEach((toggle) => {
        toggle.classList.remove('checked');
        toggle.setAttribute('aria-checked', 'false');
    });

    // Clear all tracker toggle cookies
    document.querySelectorAll('.tracker-toggle').forEach((toggle) => {
        const trackerId = toggle.dataset.trackerId;
        const entryId = toggle.dataset.entryId;
        if (characterId && trackerId && entryId) {
            const cookieKey = getTrackerToggleCookieKey(characterId, trackerId, entryId);
            setCookieValue(cookieKey, JSON.stringify([]), ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        }
    });

    // Also clear tracker bar toggles
    document.querySelectorAll('#tracker-bar-inner .tracker-toggle.checked').forEach((toggle) => {
        toggle.classList.remove('checked');
        toggle.setAttribute('aria-checked', 'false');
    });

    // 2. Reset temp HP to empty (shows the "--" placeholder) and current HP
    // to health points total
    const healthPointsField = document.getElementById('character-health_points');
    const tempHpField = document.getElementById('character-temporary_hit_points');
    const currentHpField = document.getElementById('character-current_health_points');

    if (tempHpField) {
        tempHpField.value = '';
        tempHpField.dispatchEvent(new Event('input', { bubbles: true }));
    }

    if (healthPointsField && currentHpField) {
        const hp = parseInt(healthPointsField.value, 10);
        currentHpField.value = isNaN(hp) ? '' : hp;
        currentHpField.dispatchEvent(new Event('input', { bubbles: true }));

        // Save to cookie
        if (characterId) {
            const cookieKey = `current_hp_${characterId}`;
            setCookieValue(cookieKey, currentHpField.value, CURRENT_HP_COOKIE_MAX_AGE_SECONDS);
        }
    }

    // 3. Reset all Hit Dice counters back to full
    document.querySelectorAll('.hit-dice-tracker-item').forEach((item) => {
        const classId = item.dataset.classId;
        if (characterId && classId) {
            setCookieValue(getHitDiceUsedCookieKey(characterId, classId), '0', ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        }
        renderHitDiceRemaining(item);
    });
}

function bindTrackerAddEntryToggles() {
    const showEl = (el) => { if (el) el.style.display = 'flex'; };
    const hideEl = (el) => { if (el) el.style.display = 'none'; };

    // ── Full Rest button ──
    document.querySelectorAll('[data-full-rest-btn="true"]').forEach((fullRestBtn) => {
        if (fullRestBtn.dataset.bound === 'true') return;
        fullRestBtn.dataset.bound = 'true';
        fullRestBtn.addEventListener('click', performFullRest);
    });

    // ── Per-tracker "Add Entry" toggles ──
    document.querySelectorAll('.tracker-add-entry-btn').forEach((btn) => {
        if (btn.dataset.bound === 'true') return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => {
            const tid = btn.dataset.trackerId;
            hideEl(document.getElementById(`add-entry-btn-wrapper-${tid}`));
            showEl(document.getElementById(`add-entry-field-name-${tid}`));
            showEl(document.getElementById(`add-entry-field-value-${tid}`));
            showEl(document.getElementById(`add-entry-submit-wrapper-${tid}`));
            showEl(document.getElementById(`add-entry-close-wrapper-${tid}`));
        });
    });

    document.querySelectorAll('.tracker-add-entry-close-btn').forEach((btn) => {
        if (btn.dataset.bound === 'true') return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => {
            const tid = btn.dataset.trackerId;
            showEl(document.getElementById(`add-entry-btn-wrapper-${tid}`));
            hideEl(document.getElementById(`add-entry-field-name-${tid}`));
            hideEl(document.getElementById(`add-entry-field-value-${tid}`));
            hideEl(document.getElementById(`add-entry-submit-wrapper-${tid}`));
            hideEl(document.getElementById(`add-entry-close-wrapper-${tid}`));
        });
    });

    // ── "Add Tracker" toggle ──
    const addTrackerBtn = document.getElementById('add-tracker-btn');
    const addTrackerBtnWrapper = document.getElementById('add-tracker-btn-wrapper');
    const addTrackerFieldName = document.getElementById('add-tracker-field-name');
    const addTrackerSubmitWrapper = document.getElementById('add-tracker-submit-wrapper');
    const addTrackerCloseWrapper = document.getElementById('add-tracker-close-wrapper');
    const addTrackerCloseBtn = document.getElementById('add-tracker-close-btn');

    if (addTrackerBtn && !addTrackerBtn.dataset.bound) {
        addTrackerBtn.dataset.bound = 'true';
        addTrackerBtn.addEventListener('click', () => {
            hideEl(addTrackerBtnWrapper);
            showEl(addTrackerFieldName);
            showEl(addTrackerSubmitWrapper);
            showEl(addTrackerCloseWrapper);
        });
    }

    if (addTrackerCloseBtn && !addTrackerCloseBtn.dataset.bound) {
        addTrackerCloseBtn.dataset.bound = 'true';
        addTrackerCloseBtn.addEventListener('click', () => {
            showEl(addTrackerBtnWrapper);
            hideEl(addTrackerFieldName);
            hideEl(addTrackerSubmitWrapper);
            hideEl(addTrackerCloseWrapper);
        });
    }
}

// ── Tracker auto-save ────────────────────────────────────────────────────────

let trackerAutoSaveTimers = {};

function bindTrackerAutoSave() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) return;

    document.querySelectorAll('.tracker-item').forEach((item) => {
        const trackerId = item.dataset.trackerId;
        if (!trackerId || trackerId === 'death-saves') return;

        const nameInput = item.querySelector('.tracker-name-input');
        const entryNameInputs = item.querySelectorAll('.tracker-entry-name-input');
        const entryValueInputs = item.querySelectorAll('.tracker-entry-value-input');

        const triggerAutoSave = () => {
            if (trackerAutoSaveTimers[trackerId]) {
                clearTimeout(trackerAutoSaveTimers[trackerId]);
            }
            trackerAutoSaveTimers[trackerId] = setTimeout(() => {
                trackerAutoSaveTimers[trackerId] = null;

                const liveItem = document.getElementById(`tracker-item-${trackerId}`);
                if (!liveItem) {
                    return;
                }

                const liveNameInput = liveItem.querySelector('.tracker-name-input');
                const liveEntryNameInputs = liveItem.querySelectorAll('.tracker-entry-name-input');
                const liveEntryValueInputs = liveItem.querySelectorAll('.tracker-entry-value-input');

                const values = {};
                if (liveNameInput) {
                    values['tracker-name'] = liveNameInput.value;
                }
                liveEntryNameInputs.forEach((input) => {
                    const eid = input.dataset.entryId;
                    if (eid) values[`entry-name-${eid}`] = input.value;
                });
                liveEntryValueInputs.forEach((input) => {
                    const eid = input.dataset.entryId;
                    if (eid) values[`entry-value-${eid}`] = input.value;
                });

                htmx.ajax('POST', `/characters/${characterId}/tracker/${trackerId}/update`, {
                    source: liveNameInput || liveItem,
                    target: `#tracker-item-${trackerId}`,
                    swap: 'outerHTML',
                    values: values,
                });
            }, 1000);
        };

        const allInputs = [nameInput, ...entryNameInputs, ...entryValueInputs];
        allInputs.forEach((input) => {
            if (!input || input.dataset.autoSaveBound === 'true') return;
            input.dataset.autoSaveBound = 'true';
            input.addEventListener('input', triggerAutoSave);
        });
    });
}

// ── Sub-bar tab navigation ───────────────────────────────────────────────────

function bindSubBarTabs() {
    const tabs = document.querySelectorAll('.sub-bar-tab[data-tab]');
    if (!tabs.length) return;
    const mobileTabSelect = document.getElementById('sub-bar-mobile-tab-select');

    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';

    const pages = {
        'info':      document.getElementById('sheet-page-info'),
        'inventory': document.getElementById('sheet-page-inventory'),
        'trackers':  document.getElementById('sheet-page-trackers'),
    };

    const cookieKey = characterId ? `sub_bar_tab_${characterId}` : null;
    const savedTab = cookieKey ? getCookieValue(cookieKey) : null;
    const validTabs = ['info', 'inventory', 'trackers'];
    const initialTab = (savedTab && validTabs.includes(savedTab)) ? savedTab : 'info';

    const switchTo = (tabName) => {
        // Flush every section's pending autosaves before hiding the current tab's
        // content — don't rely on display:none forcing a blur to trigger this.
        // Harmless no-op for any section with nothing pending.
        flushAllPendingFeats();
        flushAllPendingInventory();
        flushAllPendingAbilities();
        flushPendingCharacterInfo();
        flushPendingClassLevels();
        flushAllPendingCustomStats();

        // Update active class on tab buttons
        tabs.forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        if (mobileTabSelect && mobileTabSelect.value !== tabName) {
            mobileTabSelect.value = tabName;
        }

        // Show/hide sub-pages
        Object.entries(pages).forEach(([name, el]) => {
            if (!el) return;
            el.classList.toggle('d-none', name !== tabName);
        });

        // Show/hide Full Rest button (only on trackers tab)
        document.querySelectorAll('[data-full-rest-btn="true"]').forEach((fullRestBtn) => {
            fullRestBtn.classList.toggle('d-none', tabName !== 'trackers');
        });

        // Persist choice
        if (cookieKey) {
            setCookieValue(cookieKey, tabName, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        }

        // Re-bind sub-section bindings when switching into it
        if (tabName === 'trackers') {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            bindHitDiceSteppers();
            syncGlobalLockState();
            bindTrackerAutoSave();
            bindCurrentHpCalculation();
            selectCustomBuffField();
            bindBuffCardEdit();
            decorateBuffedLabels();
        } else if (tabName === 'inventory') {
            selectInventoryField();
            bindInventoryDescriptionDisplayAutoHeight();
            syncGlobalLockState();
        } else if (tabName === 'info') {
            bindFeatDescriptionDisplayAutoHeight();
            syncGlobalLockState();
        }
    };

    // Bind click handlers (guard against double-binding)
    tabs.forEach((btn) => {
        if (btn.dataset.bound === 'true') return;
        btn.dataset.bound = 'true';
        btn.addEventListener('click', () => switchTo(btn.dataset.tab));
    });

    if (mobileTabSelect && mobileTabSelect.dataset.bound !== 'true') {
        mobileTabSelect.dataset.bound = 'true';
        mobileTabSelect.addEventListener('change', () => {
            const selected = String(mobileTabSelect.value || '').trim();
            if (validTabs.includes(selected)) {
                switchTo(selected);
            }
        });
    }

    // Apply saved/default tab on load
    switchTo(initialTab);
}

// ── Theme panel ─────────────────────────────────────────────────────────────

/**
 * Map of CSS-var-name → { field: 'form_field_name', defaultValue: '...' }
 * Must stay in sync with THEME_DEFAULTS in auth/models.py.
 */
const THEME_VAR_MAP = {
    '--primary-color':        { field: 'background_colour',   default: '#ffffff' },
    '--secondary-color-dark': { field: 'border_colour',       default: 'rgb(0, 189, 91)' },
    '--label-colour':         { field: 'label_colour',        default: 'rgb(255, 255, 255)' },
    '--critical-colour':      { field: 'critical_colour',     default: 'rgb(220, 50, 50)' },
    '--success-colour':       { field: 'success_colour',      default: 'rgb(0, 189, 91)' },
    '--tracker-fill-colour':  { field: 'tracker_fill_colour', default: 'rgb(0, 153, 74)' },
    '--text-colour-one':      { field: 'asterisk_colour',     default: 'rgb(255, 0, 234)' },
    '--text-colour-three':    { field: 'field_text_colour',   default: 'rgb(255, 255, 255)' },
    '--level-colour':         { field: 'level_colour',        default: 'rgb(255, 0, 234)' },
    '--button-icon-colour':   { field: 'button_icon_colour',  default: 'rgb(255, 255, 255)' },
    '--title-colour':         { field: 'title_colour',        default: 'rgb(0, 0, 0)' },
    '--field-bg-colour':      { field: 'field_bg_colour',     default: 'rgba(0, 0, 0, 0.85)' },
};

/** Convert any rgb/rgba/hex/named colour to a hex string for <input type=color>. */
function colourToHex(colour) {
    if (!colour) return '#000000';
    const c = colour.trim();
    // Already a 6-digit hex
    if (/^#[0-9a-fA-F]{6}$/.test(c)) return c.toLowerCase();
    // 3-digit hex → expand
    if (/^#[0-9a-fA-F]{3}$/.test(c)) {
        return '#' + c[1] + c[1] + c[2] + c[2] + c[3] + c[3];
    }
    // rgb / rgba — extract r,g,b and convert
    const m = c.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/);
    if (m) {
        return '#' + [m[1], m[2], m[3]]
            .map(n => {
                const h = Math.round(Math.min(255, Math.max(0, parseFloat(n)))).toString(16);
                return h.length === 1 ? '0' + h : h;
            })
            .join('');
    }
    // Named colour — render into a temporary element
    try {
        const tmp = document.createElement('div');
        tmp.style.color = c;
        document.body.appendChild(tmp);
        const computed = getComputedStyle(tmp).color;
        document.body.removeChild(tmp);
        const m2 = computed.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/);
        if (m2) {
            return '#' + [m2[1], m2[2], m2[3]]
                .map(n => {
                    const h = Math.round(parseFloat(n)).toString(16);
                    return h.length === 1 ? '0' + h : h;
                })
                .join('');
        }
    } catch (_) {}
    return '#000000';
}

/** Read the current live value of a CSS custom property from :root. */
function getLiveCssVar(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

/** Resolve any CSS colour string to computed rgb()/rgba() form. */
function resolveToComputedColour(colour) {
    if (!colour) return '';
    try {
        const tmp = document.createElement('div');
        tmp.style.color = colour;
        document.body.appendChild(tmp);
        const computed = getComputedStyle(tmp).color;
        document.body.removeChild(tmp);
        return computed;
    } catch (_) {
        return '';
    }
}

/** Pick a readable foreground (dark/light) for a supplied background colour. */
function getReadableForegroundFor(colour) {
    const resolved = resolveToComputedColour(colour);
    const m = resolved.match(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)/i);
    if (!m) return '#f8f8f8';

    const r = Math.max(0, Math.min(255, parseFloat(m[1])));
    const g = Math.max(0, Math.min(255, parseFloat(m[2])));
    const b = Math.max(0, Math.min(255, parseFloat(m[3])));
    const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    return luminance > 0.6 ? '#121212' : '#f8f8f8';
}

/** Style one theme-panel row so the text field matches its attached colour. */
function syncThemeRowPreview(row, colourValue) {
    if (!row) return;

    const picker = row.querySelector('.theme-colour-picker');
    const text = row.querySelector('.theme-colour-text');
    if (!text) return;

    const colour = String(colourValue || '').trim();
    if (!colour) {
        if (picker) picker.style.removeProperty('border-color');
        text.style.removeProperty('background');
        text.style.removeProperty('color');
        if (!text.classList.contains('is-invalid')) {
            text.style.removeProperty('border-color');
        }
        return;
    }

    if (picker) {
        picker.style.borderColor = colour;
    }

    text.style.background = colour;
    text.style.color = getReadableForegroundFor(colour);
    if (text.classList.contains('is-invalid')) {
        text.style.borderColor = 'rgba(255, 80, 80, 0.8)';
    } else {
        text.style.borderColor = colour;
    }
}

/** Apply a colour to a CSS var and immediately update the panel picker + text. */
function applyColour(varName, value) {
    document.documentElement.style.setProperty(varName, value);
}

function bindThemePanel() {
    const toggle = document.getElementById('theme-panel-toggle');
    const container = document.getElementById('theme-panel-container');
    if (!toggle || !container) return;

    const panel = container.querySelector('#theme-panel');
    const closeBtn = document.getElementById('theme-panel-close-btn');
    const cancelBtn = document.getElementById('theme-panel-cancel-btn');
    const saveBtn = document.getElementById('theme-panel-save-btn');
    const feedback = document.getElementById('theme-save-feedback');

    let savedSnapshot = {};

    /** Capture the current live CSS vars as a snapshot for revert. */
    function snapshotCurrentVars() {
        savedSnapshot = {};
        for (const varName of Object.keys(THEME_VAR_MAP)) {
            savedSnapshot[varName] = getLiveCssVar(varName) || THEME_VAR_MAP[varName].default;
        }
    }

    /** Populate all pickers and text inputs from the current live CSS vars. */
    function populateInputsFromLive() {
        container.querySelectorAll('.theme-colour-picker').forEach(picker => {
            const varName = picker.dataset.var;
            if (!varName) return;
            const live = getLiveCssVar(varName) || THEME_VAR_MAP[varName].default;
            picker.value = colourToHex(live);
            // Update sibling text input
            const row = picker.closest('.theme-panel-row');
            if (row) {
                const text = row.querySelector('.theme-colour-text');
                if (text) text.value = live;
                syncThemeRowPreview(row, live);
            }
        });
    }

    /** Revert all CSS vars back to the snapshot. */
    function revertToSnapshot() {
        for (const [varName, value] of Object.entries(savedSnapshot)) {
            document.documentElement.style.setProperty(varName, value);
        }
    }

    function openPanel() {
        snapshotCurrentVars();
        populateInputsFromLive();
        container.classList.remove('d-none');
        toggle.classList.add('active');
        if (feedback) feedback.textContent = '';
    }

    function closePanel(revert) {
        if (revert) revertToSnapshot();
        container.classList.add('d-none');
        toggle.classList.remove('active');
    }

    // ── Toggle open/close ─────────────────────────────────────────────────
    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        if (container.classList.contains('d-none')) {
            openPanel();
        } else {
            closePanel(false);
        }
    });

    // ── Close on outside click ────────────────────────────────────────────
    document.addEventListener('click', (e) => {
        if (!container.classList.contains('d-none') &&
            !container.contains(e.target) &&
            e.target !== toggle) {
            closePanel(false);
        }
    });
    container.addEventListener('click', (e) => e.stopPropagation());

    // ── Close / cancel buttons ────────────────────────────────────────────
    if (closeBtn) closeBtn.addEventListener('click', () => closePanel(true));
    if (cancelBtn) cancelBtn.addEventListener('click', () => closePanel(true));

    // ── Live preview: picker input ─────────────────────────────────────────
    container.querySelectorAll('.theme-colour-picker').forEach(picker => {
        picker.addEventListener('input', () => {
            const varName = picker.dataset.var;
            if (!varName) return;
            const hex = picker.value;
            applyColour(varName, hex);
            // Sync text input
            const row = picker.closest('.theme-panel-row');
            if (row) {
                const text = row.querySelector('.theme-colour-text');
                if (text) {
                    text.value = hex;
                    text.classList.remove('is-invalid');
                }
                syncThemeRowPreview(row, hex);
            }
        });
    });

    // ── Live preview: text input ──────────────────────────────────────────
    container.querySelectorAll('.theme-colour-text').forEach(text => {
        text.addEventListener('input', () => {
            const row = text.closest('.theme-panel-row');
            if (!row) return;
            const picker = row.querySelector('.theme-colour-picker');
            const varName = picker ? picker.dataset.var : null;
            if (!varName) return;
            const val = text.value.trim();
            if (!val) return;
            // Validate using a temporary element
            const tmp = document.createElement('div');
            tmp.style.color = val;
            document.body.appendChild(tmp);
            const computed = getComputedStyle(tmp).color;
            document.body.removeChild(tmp);
            const validColour = computed !== '' && computed !== 'rgba(0, 0, 0, 0)' || val.toLowerCase() === 'transparent';
            if (validColour) {
                text.classList.remove('is-invalid');
                applyColour(varName, val);
                if (picker) {
                    try { picker.value = colourToHex(val); } catch (_) {}
                }
                syncThemeRowPreview(row, val);
            } else {
                text.classList.add('is-invalid');
                if (picker) {
                    syncThemeRowPreview(row, picker.value);
                }
            }
        });
    });

    // ── Save via fetch ────────────────────────────────────────────────────
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const formData = new FormData();
            panel.querySelectorAll('.theme-colour-text').forEach(input => {
                if (input.name) formData.append(input.name, input.value.trim());
            });
            const meta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = meta ? meta.getAttribute('content') : '';
            saveBtn.disabled = true;
            try {
                const response = await fetch('/user/theme/save', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData,
                });
                if (response.ok) {
                    snapshotCurrentVars();
                    if (feedback) {
                        feedback.textContent = 'Saved!';
                        setTimeout(() => { if (feedback) feedback.textContent = ''; }, 2000);
                    }
                } else {
                    if (feedback) feedback.textContent = 'Save failed.';
                }
            } catch (_) {
                if (feedback) feedback.textContent = 'Save failed.';
            } finally {
                saveBtn.disabled = false;
            }
        });
    }
}
