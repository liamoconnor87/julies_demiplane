window.addEventListener("load", () => {
    initializeUiBindings();
    bindDeleteCharacterDropdown();
    bindSubBarTabs();

    // Inject the CSRF token into every htmx AJAX request as a header.
    // Flask-WTF's CSRFProtect accepts tokens from the X-CSRFToken header,
    document.body.addEventListener('htmx:configRequest', (event) => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            event.detail.headers['X-CSRFToken'] = meta.getAttribute('content');
        }
    });

    // After a feat delete (hx-swap="delete"), update capacity visibility
    document.body.addEventListener('htmx:afterRequest', (event) => {
        const trigger = event.detail.elt;
        if (trigger && trigger.dataset.featRemove === 'true' && event.detail.successful) {
            syncFeatCapacityVisibility();
        }
        if (trigger && trigger.dataset.inventoryRemove === 'true' && event.detail.successful) {
            syncInventoryCapacityVisibility();
        }
        if (trigger && trigger.dataset.inventoryDelete === 'true' && event.detail.successful) {
            syncInventoryCapacityVisibility();
        }
    });

    document.body.addEventListener('htmx:afterSwap', (event) => {
        const target = event.detail.target || event.target;
        if (!target || !target.id) {
            return;
        }

        // Re-open the auth dropdown if a validation error was returned
        if (target.id === 'auth-dropdown') {
            if (target.querySelector('.auth-error')) {
                const toggle = target.querySelector('.dropdown-toggle');
                if (toggle) {
                    const dropdown = new bootstrap.Dropdown(toggle);
                    dropdown.show();
                }
            }
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
            syncGlobalLockState();
            decorateBuffedLabels();
            bindCharacterInfoAutoSave();

            // When a new character is saved for the first time, reveal the
            // rest of the sheet sections that were hidden during creation.
            const sheetContent = document.getElementById('sheet-content');
            if (sheetContent && sheetContent.dataset.isNew === 'true') {
                sheetContent.dataset.isNew = 'false';
                document.querySelectorAll('.new-char-hidden').forEach(el => {
                    el.classList.remove('new-char-hidden');
                });
            }
            return;
        }

        if (target.id === 'classes-section-container') {
            bindAddActionButtons();
            bindClassLevelAutoSave();
            syncGlobalLockState();
            return;
        }

        if (target.id === 'feats-section-container') {
            selectFeatField();
            setTimeout(() => bindFeatDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindFeatAutoSave();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'feats-list') {
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
            return;
        }

        // Individual feat row update (outerHTML swap)
        if (target.id && target.id.startsWith('feat-row-')) {
            setTimeout(() => bindFeatDescriptionDisplayAutoHeight(), 0);
            bindFeatAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'abilities-section-container') {
            bindProficiencyToggles();
            syncGlobalLockState();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'inventory-section-container') {
            selectInventoryField();
            setTimeout(() => bindInventoryDescriptionDisplayAutoHeight(), 0);
            syncGlobalLockState();
            bindInventoryAutoSave();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'inventory-list') {
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
            return;
        }

        // Individual inventory row update (outerHTML swap)
        if (target.id && target.id.startsWith('inventory-row-')) {
            setTimeout(() => bindInventoryDescriptionDisplayAutoHeight(), 0);
            bindInventoryAutoSave();
            syncGlobalLockState();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'tracker-page-container') {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            syncGlobalLockState();
            bindTrackerAutoSave();
            return;
        }

        // Individual tracker item update (outerHTML swap)
        if (target.id && target.id.startsWith('tracker-item-')) {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            syncGlobalLockState();
            bindTrackerAutoSave();
            return;
        }

        if (target.id === 'custom-stats-section-container') {
            bindAddActionButtons();
            syncGlobalLockState();
            bindCustomStatAutoSave();
            selectCustomBuffField();
            bindBuffCardEdit();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'custom-buffs-section-container') {
            selectCustomBuffField();
            bindProficiencyToggles();
            syncGlobalLockState();
            bindCurrentHpCalculation();
            bindCombatFieldAutoSave();
            bindBuffCardEdit();
            decorateBuffedLabels();
        }

        if (target.id === 'combat-stats-section-container') {
            bindCurrentHpCalculation();
            bindCombatFieldAutoSave();
            syncGlobalLockState();
        }
    });
})

let featDescriptionResizeWindowBound = false;
let inventoryDescriptionResizeWindowBound = false;
const ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 5;
const CURRENT_HP_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

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

// ── Delete-character dropdown ────────────────────────────────────────────────

/**
 * Wire up the toggle button to show/hide the confirmation dropdown,
 * and close it when clicking outside.
 */
function bindDeleteCharacterDropdown() {
    const toggle = document.getElementById('delete-character-toggle');
    const dropdown = document.getElementById('delete-character-dropdown');
    if (!toggle || !dropdown) return;

    toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('d-none');
        // Focus the input when opening
        if (!dropdown.classList.contains('d-none')) {
            const input = dropdown.querySelector('#delete-confirm-input');
            if (input) input.focus();
        }
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && e.target !== toggle) {
            dropdown.classList.add('d-none');
        }
    });

    // Prevent clicks inside the dropdown from closing it
    dropdown.addEventListener('click', (e) => e.stopPropagation());

    bindDeleteConfirmInput();
}

/**
 * Enable the confirm button only when the input value is exactly "DELETE".
 */
function bindDeleteConfirmInput() {
    const input = document.getElementById('delete-confirm-input');
    const btn = document.getElementById('delete-confirm-btn');
    if (!input || !btn) return;

    input.addEventListener('input', () => {
        if (input.value.trim() === 'DELETE') {
            btn.removeAttribute('disabled');
        } else {
            btn.setAttribute('disabled', '');
        }
    });
}

function initializeUiBindings() {
    bindAddActionButtons();
    selectFeatField();
    selectInventoryField();
    selectCustomBuffField();
    bindClassLevelAutoSave();
    bindCustomStatAutoSave();
    bindProficiencyToggles();
    bindCurrentHpCalculation();
    bindCombatFieldAutoSave();
    bindBuffCardEdit();
    bindFeatDescriptionDisplayAutoHeight();
    bindInventoryDescriptionDisplayAutoHeight();
    decorateBuffedLabels();
    bindCharacterInfoAutoSave();
    bindFeatAutoSave();
    bindInventoryAutoSave();
    bindFeatsContainerSettle();
    bindInventoryContainerSettle();
    bindGlobalLockToggle();
    bindTrackerAutoSave();
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
}

let featAutoSaveTimers = {};

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

        const triggerAutoSave = () => {
            if (featAutoSaveTimers[featId]) {
                clearTimeout(featAutoSaveTimers[featId]);
            }
            featAutoSaveTimers[featId] = setTimeout(() => {
                featAutoSaveTimers[featId] = null;
                htmx.ajax('POST', `/characters/${characterId}/feat-and-trait/${featId}/update`, {
                    target: `#feat-row-${featId}`,
                    swap: 'outerHTML',
                    values: {
                        [`feat_and_trait-name-${featId}`]: nameInput.value,
                        [`feat_and_trait-description-${featId}`]: descInput ? descInput.value : '',
                    }
                });
            }, 1000);
        };

        [nameInput, descInput].forEach((input) => {
            if (!input || input.dataset.autoSaveBound === 'true') return;
            input.dataset.autoSaveBound = 'true';
            input.addEventListener('input', triggerAutoSave);
        });
    });
}

let characterInfoAutoSaveTimer = null;

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

    const form = section.closest('form');
    if (!form) {
        return;
    }

    const inputs = section.querySelectorAll('input:not([type="hidden"]):not([disabled])');

    const triggerAutoSave = () => {
        if (characterInfoAutoSaveTimer) {
            clearTimeout(characterInfoAutoSaveTimer);
        }
        characterInfoAutoSaveTimer = setTimeout(() => {
            characterInfoAutoSaveTimer = null;
            htmx.ajax('POST', `/characters/${characterId}/character-info/fragment`, {
                source: form,
                target: '#character-info-section-container',
                swap: 'innerHTML'
            });
        }, 1000);
    };

    inputs.forEach((input) => {
        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', triggerAutoSave);
    });
}

let classLevelAutoSaveTimer = null;

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

    const form = classesSection.closest('form');
    if (!form) {
        return;
    }

    const inputs = classesSection.querySelectorAll('.class-level-input');

    const triggerAutoSave = () => {
        if (classLevelAutoSaveTimer) {
            clearTimeout(classLevelAutoSaveTimer);
        }
        classLevelAutoSaveTimer = setTimeout(() => {
            classLevelAutoSaveTimer = null;
            htmx.ajax('POST', `/characters/${characterId}/classes/fragment`, {
                source: form,
                target: '#classes-section-container',
                swap: 'innerHTML'
            });
        }, 1000);
    };

    inputs.forEach((input) => {
        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', triggerAutoSave);
    });
}

let customStatAutoSaveTimer = null;

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

    const form = statsSection.closest('form');
    if (!form) {
        return;
    }

    const inputs = statsSection.querySelectorAll('.custom-stats-section-input[type="number"]');

    const triggerAutoSave = () => {
        if (customStatAutoSaveTimer) {
            clearTimeout(customStatAutoSaveTimer);
        }
        customStatAutoSaveTimer = setTimeout(() => {
            customStatAutoSaveTimer = null;
            htmx.ajax('POST', `/characters/${characterId}/custom-stats/fragment`, {
                source: form,
                target: '#custom-stats-section-container',
                swap: 'innerHTML'
            });
        }, 1000);
    };

    inputs.forEach((input) => {
        if (input.dataset.autoSaveBound === 'true') return;
        input.dataset.autoSaveBound = 'true';
        input.addEventListener('input', triggerAutoSave);
    });
}

function bindClassesAndStatsLockToggle() {
    syncGlobalLockState();
}

function bindBuffsLockToggle() {
    syncGlobalLockState();
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
    };

    const cards = section.querySelectorAll('.custom-buffs-card[data-buff-edit="true"]');
    cards.forEach((card) => {
        if (card.dataset.editBound === 'true') return;
        card.dataset.editBound = 'true';

        card.addEventListener('click', (e) => {
            if (e.target.closest('.custom-buffs-remove-btn')) return;
            if (section.dataset.locked === 'true') return;

            const buffId = card.dataset.buffId;
            const buffName = card.dataset.buffName;
            const buffValue = card.dataset.buffValue;
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

    // ── Classes & custom stats section ──
    const statsSection = document.querySelector('.custom-stats-section');
    if (statsSection) {
        statsSection.dataset.locked = String(isLocked);
    }
    document.querySelectorAll('[data-custom-stat-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });
    document.querySelectorAll('[data-class-remove="true"]').forEach((button) => {
        button.disabled = isLocked;
        button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
    });

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
        if (input && input.id) {
            return document.querySelector(`label[for="${input.id}"]`);
        }
        return null;
    }

    if (table === 'inventory') {
        const input = document.getElementById(`inventory-name-${normalizedStat}`);
        if (input && input.id) {
            return document.querySelector(`label[for="${input.id}"]`);
        }
        return null;
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

function bindAddActionButtons() {
    const addClassBtn = document.getElementById('add-class-btn');
    const addClassBtnWrapper = document.getElementById('add-class-btn-wrapper');
    const addCustomStatBtn = document.getElementById('add-custom-stat-btn');
    const addCustomStatBtnWrapper = document.getElementById('add-custom-stat-btn-wrapper');

    const addClassFieldDropdown = document.getElementById('add-class-field-dropdown');
    const addClassFieldLevel = document.getElementById('add-class-field-level');
    const addClassSubmitBtn = document.getElementById('add-class-submit-btn');

    const addCustomStatFieldName = document.getElementById('add-custom-stat-field-name');
    const addCustomStatFieldValue = document.getElementById('add-custom-stat-field-value');
    const addCustomStatSubmitBtnWrapper = document.getElementById('add-custom-stat-submit-btn-wrapper');

    const closeBtn = document.getElementById('close-add-action-field-x-btn');
    const closeBtnWrapper = document.getElementById('close-add-action-btn-wrapper');

    const showElement = (el) => { if (el) el.style.display = 'flex'; };
    const showBlockElement = (el) => { if (el) el.style.display = 'block'; };
    const hideElement = (el) => { if (el) el.style.display = 'none'; };

    const hideAllForms = () => {
        showElement(addClassBtnWrapper);
        showElement(addCustomStatBtnWrapper);
        hideElement(addClassFieldDropdown);
        hideElement(addClassFieldLevel);
        hideElement(addClassSubmitBtn);
        hideElement(addCustomStatFieldName);
        hideElement(addCustomStatFieldValue);
        hideElement(addCustomStatSubmitBtnWrapper);
        hideElement(closeBtnWrapper);
    };

    if (addClassBtn) {
        addClassBtn.addEventListener('click', () => {
            hideElement(addClassBtnWrapper);
            hideElement(addCustomStatBtnWrapper);
            showBlockElement(addClassFieldDropdown);
            showElement(addClassFieldLevel);
            showElement(addClassSubmitBtn);
            showElement(closeBtnWrapper);
        });
    }

    if (addCustomStatBtn) {
        addCustomStatBtn.addEventListener('click', () => {
            hideElement(addClassBtnWrapper);
            hideElement(addCustomStatBtnWrapper);
            showElement(addCustomStatFieldName);
            showElement(addCustomStatFieldValue);
            showElement(addCustomStatSubmitBtnWrapper);
            showElement(closeBtnWrapper);
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', hideAllForms);
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

    addFeatBtn.addEventListener('click', () => {
        addFeatBtnWrapper.style.display = 'none';
        addFeatFieldName.style.display = 'flex';
        addFeatFieldDescription.style.display = 'flex';
        addFeatSubmitBtnWrapper.style.display = 'flex';
        closeFeatBtnWrapper.style.display = 'flex';

        const addDescriptionField = addFeatFieldDescription.querySelector('.card-item-description-input');
        if (addDescriptionField) {
            addDescriptionField.style.height = '';
            resizeFeatDescriptionField(addDescriptionField);
        }
    });

    closeFeatFieldXBtn.addEventListener('click', () => {
        addFeatBtnWrapper.style.display = 'flex';
        addFeatFieldName.style.display = 'none';
        addFeatFieldDescription.style.display = 'none';
        addFeatSubmitBtnWrapper.style.display = 'none';
        closeFeatBtnWrapper.style.display = 'none';
    });
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

    closeInventoryFieldXBtn.addEventListener('click', () => {
        addInventoryBtnWrapper.style.display = 'flex';
        addInventoryFieldName.style.display = 'none';
        addInventoryFieldQuantity.style.display = 'none';
        addInventoryFieldDescription.style.display = 'none';
        addInventorySubmitBtnWrapper.style.display = 'none';
        closeInventoryBtnWrapper.style.display = 'none';
    });
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

let inventoryAutoSaveTimers = {};

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

        const triggerAutoSave = () => {
            if (inventoryAutoSaveTimers[inventoryId]) {
                clearTimeout(inventoryAutoSaveTimers[inventoryId]);
            }
            inventoryAutoSaveTimers[inventoryId] = setTimeout(() => {
                inventoryAutoSaveTimers[inventoryId] = null;
                htmx.ajax('POST', `/characters/${characterId}/inventory/${inventoryId}/update`, {
                    target: `#inventory-row-${inventoryId}`,
                    swap: 'outerHTML',
                    values: {
                        [`inventory-name-${inventoryId}`]: nameInput.value,
                        [`inventory-description-${inventoryId}`]: descInput ? descInput.value : '',
                    }
                });
            }, 1000);
        };

        [nameInput, descInput].forEach((input) => {
            if (!input || input.dataset.autoSaveBound === 'true') return;
            input.dataset.autoSaveBound = 'true';
            input.addEventListener('input', triggerAutoSave);
        });
    });
}

function bindCurrentHpCalculation() {
    const healthPointsField = document.getElementById('character-health_points');
    const tempHpField = document.getElementById('character-temporary_hit_points');
    const currentHpField = document.getElementById('character-current_health_points');
    const decreaseCurrentHpBtn = document.getElementById('decrease-current-hp-btn');
    const increaseCurrentHpBtn = document.getElementById('increase-current-hp-btn');

    if (!healthPointsField || !tempHpField || !currentHpField) {
        return;
    }

    // Guard against duplicate listener binding — combat fields survive
    // across character-info and custom-buffs swaps, so listeners accumulate
    // without this check.
    if (currentHpField.dataset.hpCalcBound === 'true') {
        return;
    }
    currentHpField.dataset.hpCalcBound = 'true';

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

    const parseNumberOrZero = (value) => {
        if (value === '--' || value === '') return 0;
        const parsed = Number.parseInt(value, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const displayTempHp = (numericValue) => {
        tempHpField.value = numericValue > 0 ? numericValue : '--';
    };

    const getMaxCurrentHp = () => {
        const healthPoints = parseNumberOrZero(healthPointsField.value);
        const tempHp = parseNumberOrZero(tempHpField.value);
        return Math.max(0, healthPoints + tempHp);
    };

    // Restore from cookie on initial bind
    const cookieKey = getCurrentHpCookieKey();
    const savedHp = cookieKey ? getCookieValue(cookieKey) : null;
    if (savedHp !== null && savedHp !== '') {
        const maxCurrentHp = getMaxCurrentHp();
        const restoredHp = Math.min(maxCurrentHp, Math.max(0, parseNumberOrZero(savedHp)));
        currentHpField.value = restoredHp;
    }

    let previousMaxCurrentHp = getMaxCurrentHp();

    const adjustCurrentHp = (delta) => {
        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxCurrentHp = getMaxCurrentHp();

        if (delta > 0) {
            currentHpField.value = Math.min(maxCurrentHp, currentHp + delta);
            saveCurrentHpToCookie();
            return;
        }

        if (delta < 0) {
            if (currentHp <= 0) {
                currentHpField.value = 0;
                saveCurrentHpToCookie();
                return;
            }

            const tempHp = parseNumberOrZero(tempHpField.value);
            if (tempHp > 0) {
                displayTempHp(tempHp - 1);
                tempHpField.dispatchEvent(new Event('input', { bubbles: true }));
            }

            currentHpField.value = Math.max(0, currentHp + delta);
            saveCurrentHpToCookie();
        }
    };

    const calculateCurrentHp = () => {
        if (healthPointsField.value === '' && tempHpField.value === '') {
            currentHpField.value = '';
            previousMaxCurrentHp = 0;
            saveCurrentHpToCookie();
            return;
        }

        const maxCurrentHp = getMaxCurrentHp();

        if (currentHpField.value === '') {
            currentHpField.value = maxCurrentHp;
            previousMaxCurrentHp = maxCurrentHp;
            saveCurrentHpToCookie();
            return;
        }

        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxDelta = maxCurrentHp - previousMaxCurrentHp;
        const adjustedCurrentHp = currentHp + maxDelta;

        currentHpField.value = Math.min(maxCurrentHp, Math.max(0, adjustedCurrentHp));
        previousMaxCurrentHp = maxCurrentHp;
        saveCurrentHpToCookie();
    };

    healthPointsField.addEventListener('input', calculateCurrentHp);
    tempHpField.addEventListener('input', calculateCurrentHp);

    tempHpField.addEventListener('focus', () => {
        if (tempHpField.value === '--') {
            tempHpField.value = '';
        }
    });

    tempHpField.addEventListener('blur', () => {
        displayTempHp(parseNumberOrZero(tempHpField.value));
    });

    if (decreaseCurrentHpBtn) {
        decreaseCurrentHpBtn.addEventListener('click', () => {
            adjustCurrentHp(-1);
        });
    }

    if (increaseCurrentHpBtn) {
        increaseCurrentHpBtn.addEventListener('click', () => {
            adjustCurrentHp(1);
        });
    }

    currentHpField.addEventListener('input', () => {
        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxCurrentHp = getMaxCurrentHp();
        currentHpField.value = Math.min(maxCurrentHp, Math.max(0, currentHp));
        saveCurrentHpToCookie();
    });

    calculateCurrentHp();
}

let combatAutoSaveTimer = null;

function bindCombatFieldAutoSave() {
    const healthPointsField = document.getElementById('character-health_points');
    const tempHpField = document.getElementById('character-temporary_hit_points');
    const hitDiceField = document.getElementById('character-hit_dice');
    const characterIdField = document.getElementById('character-id');

    if (!healthPointsField || !tempHpField || !hitDiceField || !characterIdField) {
        return;
    }

    const characterId = characterIdField.value;
    const form = healthPointsField.closest('form');
    if (!form || !characterId) {
        return;
    }

    const triggerAutoSave = () => {
        if (combatAutoSaveTimer) {
            clearTimeout(combatAutoSaveTimer);
        }
        combatAutoSaveTimer = setTimeout(() => {
            combatAutoSaveTimer = null;
            htmx.ajax('POST', `/characters/${characterId}/combat/fragment`, {
                source: form,
                target: '#combat-stats-section-container',
                swap: 'innerHTML'
            });
        }, 1000);
    };

    [healthPointsField, tempHpField, hitDiceField].forEach((field) => {
        if (field.dataset.autoSaveBound === 'true') return;
        field.dataset.autoSaveBound = 'true';
        field.addEventListener('input', triggerAutoSave);
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

function bindAbilitiesSectionLockToggle() {
    syncGlobalLockState();
}

function bindFeatDescriptionDisplayAutoHeight() {
    const descriptionFields = document.querySelectorAll('.feats-section .card-item-saved-row .card-item-description-input');

    if (!descriptionFields.length) {
        return;
    }

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

    if (!descriptionFields.length) {
        return;
    }

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

    // 2. Reset temp HP to '--' and current HP to health points total
    const healthPointsField = document.getElementById('character-health_points');
    const tempHpField = document.getElementById('character-temporary_hit_points');
    const currentHpField = document.getElementById('character-current_health_points');

    if (tempHpField) {
        tempHpField.value = '--';
        tempHpField.dispatchEvent(new Event('input', { bubbles: true }));
    }

    if (healthPointsField && currentHpField) {
        const hp = parseInt(healthPointsField.value, 10);
        currentHpField.value = isNaN(hp) ? '' : hp;

        // Save to cookie
        if (characterId) {
            const cookieKey = `current_hp_${characterId}`;
            setCookieValue(cookieKey, currentHpField.value, CURRENT_HP_COOKIE_MAX_AGE_SECONDS);
        }
    }
}

function bindTrackerAddEntryToggles() {
    const showEl = (el) => { if (el) el.style.display = 'flex'; };
    const hideEl = (el) => { if (el) el.style.display = 'none'; };

    // ── Full Rest button ──
    const fullRestBtn = document.getElementById('full-rest-btn');
    if (fullRestBtn && fullRestBtn.dataset.bound !== 'true') {
        fullRestBtn.dataset.bound = 'true';
        fullRestBtn.addEventListener('click', performFullRest);
    }

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
        if (!trackerId) return;

        const nameInput = item.querySelector('.tracker-name-input');
        const entryNameInputs = item.querySelectorAll('.tracker-entry-name-input');
        const entryValueInputs = item.querySelectorAll('.tracker-entry-value-input');

        const triggerAutoSave = () => {
            if (trackerAutoSaveTimers[trackerId]) {
                clearTimeout(trackerAutoSaveTimers[trackerId]);
            }
            trackerAutoSaveTimers[trackerId] = setTimeout(() => {
                trackerAutoSaveTimers[trackerId] = null;

                const values = {};
                if (nameInput) {
                    values['tracker-name'] = nameInput.value;
                }
                entryNameInputs.forEach((input) => {
                    const eid = input.dataset.entryId;
                    if (eid) values[`entry-name-${eid}`] = input.value;
                });
                entryValueInputs.forEach((input) => {
                    const eid = input.dataset.entryId;
                    if (eid) values[`entry-value-${eid}`] = input.value;
                });

                htmx.ajax('POST', `/characters/${characterId}/tracker/${trackerId}/update`, {
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
    const tabs = document.querySelectorAll('.sub-bar-tab');
    if (!tabs.length) return;

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
        // Update active class on tab buttons
        tabs.forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Show/hide sub-pages
        Object.entries(pages).forEach(([name, el]) => {
            if (!el) return;
            el.classList.toggle('d-none', name !== tabName);
        });

        // Show/hide Full Rest button (only on trackers tab)
        const fullRestBtn = document.getElementById('full-rest-btn');
        if (fullRestBtn) {
            fullRestBtn.classList.toggle('d-none', tabName !== 'trackers');
        }

        // Persist choice
        if (cookieKey) {
            setCookieValue(cookieKey, tabName, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
        }

        // Re-bind sub-section bindings when switching into it
        if (tabName === 'trackers') {
            bindTrackerToggles();
            bindTrackerAddEntryToggles();
            syncGlobalLockState();
            bindTrackerAutoSave();
            bindCurrentHpCalculation();
            bindCombatFieldAutoSave();
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

    // Apply saved/default tab on load
    switchTo(initialTab);
}