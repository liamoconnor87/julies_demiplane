window.addEventListener("load", () => {
    initializeUiBindings();
    bindDeleteCharacterDropdown();

    // Inject the CSRF token into every htmx AJAX request as a header.
    // Flask-WTF's CSRFProtect accepts tokens from the X-CSRFToken header,
    document.body.addEventListener('htmx:configRequest', (event) => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            event.detail.headers['X-CSRFToken'] = meta.getAttribute('content');
        }
    });

    document.body.addEventListener('htmx:afterSwap', (event) => {
        const target = event.target;
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
            bindAbilitiesSectionLockToggle();
            decorateBuffedLabels();
            bindCharacterInfoChangeDetection();

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
            bindClassLevelUpdateButtons();
            return;
        }

        if (target.id === 'feats-section-container') {
            selectFeatField();
            bindFeatDescriptionDisplayAutoHeight();
            bindFeatsLockToggle();
            return;
        }

        if (target.id === 'abilities-section-container') {
            bindProficiencyToggles();
            bindAbilitiesSectionLockToggle();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'inventory-section-container') {
            selectInventoryField();
            bindInventoryDescriptionDisplayAutoHeight();
            bindInventoryLockToggle();
            return;
        }

        if (target.id === 'custom-stats-section-container') {
            bindAddActionButtons();
            bindCustomStatsLockToggle();
            selectCustomBuffField();
            bindBuffsLockToggle();
            decorateBuffedLabels();
            return;
        }

        if (target.id === 'custom-buffs-section-container') {
            selectCustomBuffField();
            bindProficiencyToggles();
            bindAbilitiesSectionLockToggle();
            bindCurrentHpCalculation();
            bindCombatFieldAutoSave();
            bindCustomStatsLockToggle();
            bindBuffsLockToggle();
            decorateBuffedLabels();
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

function getAbilityLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }

    return `ability_skill_lock_${characterId}`;
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
    bindClassLevelUpdateButtons();
    bindProficiencyToggles();
    bindAbilitiesSectionLockToggle();
    bindCurrentHpCalculation();
    bindCombatFieldAutoSave();
    bindCustomStatsLockToggle();
    bindFeatsLockToggle();
    bindInventoryLockToggle();
    bindBuffsLockToggle();
    bindFeatDescriptionDisplayAutoHeight();
    bindInventoryDescriptionDisplayAutoHeight();
    decorateBuffedLabels();
    bindCharacterInfoChangeDetection();
}

function bindCharacterInfoChangeDetection() {
    const section = document.querySelector('.character-info-section');
    if (!section) {
        return;
    }

    section.dataset.unsaved = 'false';

    const inputs = section.querySelectorAll('input:not([type="hidden"]):not([disabled])');
    const originalValues = new Map();

    inputs.forEach((input) => {
        originalValues.set(input, input.value);
    });

    const checkForChanges = () => {
        let hasChanges = false;
        inputs.forEach((input) => {
            if (input.value !== originalValues.get(input)) {
                hasChanges = true;
            }
        });
        section.dataset.unsaved = hasChanges ? 'true' : 'false';
    };

    inputs.forEach((input) => {
        input.addEventListener('input', checkForChanges);
    });
}

function getCustomStatsLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }

    return `custom_stats_lock_${characterId}`;
}

function bindCustomStatsLockToggle() {
    const section = document.querySelector('.custom-stats-section');
    const lockToggle = document.getElementById('custom-stats-lock-toggle');

    if (!section || !lockToggle) {
        return;
    }

    const cookieKey = getCustomStatsLockCookieKey();
    const persistedLockState = cookieKey ? getCookieValue(cookieKey) : null;

    if (persistedLockState === 'true' || persistedLockState === 'false') {
        section.dataset.locked = persistedLockState;
    } else if (!section.dataset.locked) {
        section.dataset.locked = 'false';
    }

    const syncRemoveButtons = () => {
        const isLocked = section.dataset.locked === 'true';
        const removeButtons = section.querySelectorAll('[data-custom-stat-remove="true"]');
        removeButtons.forEach((button) => {
            button.disabled = isLocked;
            button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
        });
    };

    const syncLockText = () => {
        const isLocked = section.dataset.locked === 'true';
        lockToggle.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockToggle.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockToggle.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
        syncRemoveButtons();
    };

    if (lockToggle.dataset.bound !== 'true') {
        lockToggle.addEventListener('click', () => {
            const isLocked = section.dataset.locked === 'true';
            section.dataset.locked = isLocked ? 'false' : 'true';
            if (cookieKey) {
                setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncLockText();
        });

        lockToggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                const isLocked = section.dataset.locked === 'true';
                section.dataset.locked = isLocked ? 'false' : 'true';
                if (cookieKey) {
                    setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
                }
                syncLockText();
            }
        });

        lockToggle.dataset.bound = 'true';
    }

    syncLockText();
}

function getBuffsLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }

    return `buffs_lock_${characterId}`;
}

function bindBuffsLockToggle() {
    const section = document.querySelector('.custom-buffs-section');
    const lockToggle = document.getElementById('buffs-lock-toggle');

    if (!section || !lockToggle) {
        return;
    }

    const cookieKey = getBuffsLockCookieKey();
    const persistedLockState = cookieKey ? getCookieValue(cookieKey) : null;

    if (persistedLockState === 'true' || persistedLockState === 'false') {
        section.dataset.locked = persistedLockState;
    } else if (!section.dataset.locked) {
        section.dataset.locked = 'false';
    }

    const syncRemoveButtons = () => {
        const isLocked = section.dataset.locked === 'true';
        const removeButtons = section.querySelectorAll('[data-buff-remove="true"]');
        removeButtons.forEach((button) => {
            button.disabled = isLocked;
            button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
        });
    };

    const syncLockText = () => {
        const isLocked = section.dataset.locked === 'true';
        lockToggle.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockToggle.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockToggle.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
        syncRemoveButtons();
    };

    if (lockToggle.dataset.bound !== 'true') {
        lockToggle.addEventListener('click', () => {
            const isLocked = section.dataset.locked === 'true';
            section.dataset.locked = isLocked ? 'false' : 'true';
            if (cookieKey) {
                setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncLockText();
        });

        lockToggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                const isLocked = section.dataset.locked === 'true';
                section.dataset.locked = isLocked ? 'false' : 'true';
                if (cookieKey) {
                    setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
                }
                syncLockText();
            }
        });

        lockToggle.dataset.bound = 'true';
    }

    syncLockText();
}

function getFeatsLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }

    return `feats_lock_${characterId}`;
}

function bindFeatsLockToggle() {
    const section = document.querySelector('.feats-section');
    const lockToggle = document.getElementById('feats-lock-toggle');

    if (!section || !lockToggle) {
        return;
    }

    const cookieKey = getFeatsLockCookieKey();
    const persistedLockState = cookieKey ? getCookieValue(cookieKey) : null;

    if (persistedLockState === 'true' || persistedLockState === 'false') {
        section.dataset.locked = persistedLockState;
    } else if (!section.dataset.locked) {
        section.dataset.locked = 'false';
    }

    const syncRemoveButtons = () => {
        const isLocked = section.dataset.locked === 'true';
        const removeButtons = section.querySelectorAll('[data-feat-remove="true"]');
        removeButtons.forEach((button) => {
            button.disabled = isLocked;
            button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
        });
    };

    const syncLockText = () => {
        const isLocked = section.dataset.locked === 'true';
        lockToggle.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockToggle.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockToggle.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
        syncRemoveButtons();
    };

    if (lockToggle.dataset.bound !== 'true') {
        lockToggle.addEventListener('click', () => {
            const isLocked = section.dataset.locked === 'true';
            section.dataset.locked = isLocked ? 'false' : 'true';
            if (cookieKey) {
                setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncLockText();
        });

        lockToggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                const isLocked = section.dataset.locked === 'true';
                section.dataset.locked = isLocked ? 'false' : 'true';
                if (cookieKey) {
                    setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
                }
                syncLockText();
            }
        });

        lockToggle.dataset.bound = 'true';
    }

    syncLockText();
}

function getInventoryLockCookieKey() {
    const characterIdField = document.getElementById('character-id');
    const characterId = characterIdField ? String(characterIdField.value || '').trim() : '';
    if (!characterId) {
        return null;
    }

    return `inventory_lock_${characterId}`;
}

function bindInventoryLockToggle() {
    const section = document.querySelector('.inventory-section');
    const lockToggle = document.getElementById('inventory-lock-toggle');

    if (!section || !lockToggle) {
        return;
    }

    const cookieKey = getInventoryLockCookieKey();
    const persistedLockState = cookieKey ? getCookieValue(cookieKey) : null;

    if (persistedLockState === 'true' || persistedLockState === 'false') {
        section.dataset.locked = persistedLockState;
    } else if (!section.dataset.locked) {
        section.dataset.locked = 'false';
    }

    const syncRemoveButtons = () => {
        const isLocked = section.dataset.locked === 'true';
        const removeButtons = section.querySelectorAll('[data-inventory-remove="true"]');
        removeButtons.forEach((button) => {
            button.disabled = isLocked;
            button.setAttribute('aria-disabled', isLocked ? 'true' : 'false');
        });
    };

    const syncLockText = () => {
        const isLocked = section.dataset.locked === 'true';
        lockToggle.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockToggle.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockToggle.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
        syncRemoveButtons();
    };

    if (lockToggle.dataset.bound !== 'true') {
        lockToggle.addEventListener('click', () => {
            const isLocked = section.dataset.locked === 'true';
            section.dataset.locked = isLocked ? 'false' : 'true';
            if (cookieKey) {
                setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncLockText();
        });

        lockToggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                const isLocked = section.dataset.locked === 'true';
                section.dataset.locked = isLocked ? 'false' : 'true';
                if (cookieKey) {
                    setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
                }
                syncLockText();
            }
        });

        lockToggle.dataset.bound = 'true';
    }

    syncLockText();
}

function addBuffIndicator(el) {
    if (el && !el.querySelector('.buff-indicator')) {
        el.insertAdjacentHTML('beforeend', ' <span class="buff-indicator">*</span>');
    }
}

function decorateBuffedLabels() {
    // Clear any existing indicators first
    document.querySelectorAll('.buff-indicator').forEach(el => el.remove());

    const dataEl = document.getElementById('buff-fields-data');
    if (!dataEl) return;

    let buffFields;
    try {
        buffFields = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }

    if (!buffFields || !buffFields.length) return;

    buffFields.forEach(({ table, stat }) => {
        if (table === 'custom_stat') {
            // Match label by name text on custom_stat-value-* inputs
            document.querySelectorAll('label.custom-stats-section-label').forEach(label => {
                if (
                    label.textContent.trim() === stat &&
                    label.htmlFor &&
                    label.htmlFor.startsWith('custom_stat-value-')
                ) {
                    addBuffIndicator(label);
                }
            });
            return;
        }

        const key = `${table}-${stat}`;

        // Try input (character stats, ability values)
        const input = document.querySelector(`input[name="${key}"]`);
        if (input && input.id) {
            const label = document.querySelector(`label[for="${input.id}"]`);
            if (label) {
                addBuffIndicator(label);
                return;
            }
        }

        // Try display div (modifier, saving throw, skills)
        const displayDiv = document.getElementById(key);
        if (displayDiv) {
            const labelDiv = displayDiv.closest('.abilities-section-secondary-field, .abilities-section-skills-item')?.querySelector('.abilities-section-display-label');
            if (labelDiv) {
                addBuffIndicator(labelDiv);
            }
        }
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

        const addDescriptionField = addFeatFieldDescription.querySelector('.feats-section-description-input');
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

        const addDescriptionField = addInventoryFieldDescription.querySelector('.inventory-section-description-input');
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

    field.style.height = 'auto';

    const computedStyles = window.getComputedStyle(field);
    const minHeight = Number.parseFloat(computedStyles.minHeight) || field.clientHeight || 0;
    const targetHeight = Math.max(field.scrollHeight, minHeight);
    field.style.height = `${targetHeight}px`;
}

function resizeInventoryDescriptionField(field) {
    if (!field) {
        return;
    }

    field.style.height = 'auto';

    const computedStyles = window.getComputedStyle(field);
    const minHeight = Number.parseFloat(computedStyles.minHeight) || field.clientHeight || 0;
    const targetHeight = Math.max(field.scrollHeight, minHeight);
    field.style.height = `${targetHeight}px`;
}

function bindClassLevelUpdateButtons() {
    const classLevelInputs = document.querySelectorAll('.class-level-input');

    classLevelInputs.forEach((input) => {
        const classId = input.dataset.charClassId;
        const actionBtn = document.getElementById(`classes-action-${classId}`);
        const actionLabel = document.getElementById(`classes-action-label-${classId}`);

        if (!actionBtn || !actionLabel) {
            return;
        }

        const setButtonMode = () => {
            const currentValue = input.value.trim();
            const originalValue = (input.dataset.originalValue || '').trim();
            const hasChanged = currentValue !== originalValue;
            const updateUrl = actionBtn.dataset.htmxUpdateUrl;
            const removeUrl = actionBtn.dataset.removeUrl;

            if (hasChanged) {
                actionBtn.type = 'button';
                actionBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
                actionLabel.textContent = 'Update';
                if (updateUrl) {
                    actionBtn.setAttribute('hx-post', updateUrl);
                }
                actionBtn.setAttribute('hx-target', '#classes-section-container');
                actionBtn.setAttribute('hx-swap', 'innerHTML');
                actionBtn.setAttribute('hx-include', 'closest form');
                htmx.process(actionBtn);
                return;
            }

            actionBtn.type = 'button';
            actionBtn.textContent = '−';
            actionLabel.textContent = 'Remove';
            if (removeUrl) {
                actionBtn.setAttribute('hx-post', removeUrl);
            }
            actionBtn.setAttribute('hx-target', '#classes-section-container');
            actionBtn.setAttribute('hx-swap', 'innerHTML');
            actionBtn.setAttribute('hx-include', 'closest form');
            htmx.process(actionBtn);
        };

        setButtonMode();
        input.addEventListener('input', setButtonMode);
        input.addEventListener('change', setButtonMode);
    });
}

// Function to update inventory item quantity
function updateInventoryItem(itemId) {
    const qtyInput = document.getElementById('inventory-quantity-' + itemId);
    const newQuantity = qtyInput.value;

    // You can implement this as a fetch request or form submission
    // For now, this will trigger the main form save
    alert('Update inventory quantity to ' + newQuantity + ' - Click Save at the bottom to persist changes');
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
            htmx.ajax('POST', `/characters/${characterId}/character-info/fragment`, {
                source: form,
                target: '#character-info-section-container',
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
    const section = document.querySelector('.abilities-section');
    const lockToggle = document.getElementById('abilities-lock-toggle');

    if (!section || !lockToggle) {
        return;
    }

    const cookieKey = getAbilityLockCookieKey();
    const persistedLockState = cookieKey ? getCookieValue(cookieKey) : null;

    if (persistedLockState === 'true' || persistedLockState === 'false') {
        section.dataset.locked = persistedLockState;
    } else if (!section.dataset.locked) {
        section.dataset.locked = 'false';
    }

    const syncLockText = () => {
        const isLocked = section.dataset.locked === 'true';
        lockToggle.innerHTML = isLocked
            ? '<i class="bi bi-lock-fill" aria-hidden="true"></i>'
            : '<i class="bi bi-unlock-fill" aria-hidden="true"></i>';
        lockToggle.setAttribute('aria-label', isLocked ? 'Locked' : 'Unlocked');
        lockToggle.setAttribute('aria-pressed', isLocked ? 'true' : 'false');
    };

    if (lockToggle.dataset.bound !== 'true') {
        lockToggle.addEventListener('click', () => {
            const isLocked = section.dataset.locked === 'true';
            section.dataset.locked = isLocked ? 'false' : 'true';
            if (cookieKey) {
                setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
            }
            syncLockText();
        });

        lockToggle.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                const isLocked = section.dataset.locked === 'true';
                section.dataset.locked = isLocked ? 'false' : 'true';
                if (cookieKey) {
                    setCookieValue(cookieKey, section.dataset.locked, ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS);
                }
                syncLockText();
            }
        });

        lockToggle.dataset.bound = 'true';
    }

    syncLockText();
}

function bindFeatDescriptionDisplayAutoHeight() {
    const descriptionFields = document.querySelectorAll('.feats-section-description-input');

    if (!descriptionFields.length) {
        return;
    }

    descriptionFields.forEach((field) => {
        if (field.hasAttribute('readonly')) {
            resizeFeatDescriptionField(field);
        }

        if (!field.hasAttribute('readonly') && field.dataset.autoresizeBound !== 'true') {
            field.addEventListener('input', () => {
                resizeFeatDescriptionField(field);
            });
            field.dataset.autoresizeBound = 'true';
        }
    });

    if (!featDescriptionResizeWindowBound) {
        window.addEventListener('resize', () => {
            const activeDescriptionFields = document.querySelectorAll('.feats-section-description-input');
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
    const descriptionFields = document.querySelectorAll('.inventory-section-description-input');

    if (!descriptionFields.length) {
        return;
    }

    descriptionFields.forEach((field) => {
        if (field.hasAttribute('readonly')) {
            resizeInventoryDescriptionField(field);
        }

        if (!field.hasAttribute('readonly') && field.dataset.autoresizeBound !== 'true') {
            field.addEventListener('input', () => {
                resizeInventoryDescriptionField(field);
            });
            field.dataset.autoresizeBound = 'true';
        }
    });

    if (!inventoryDescriptionResizeWindowBound) {
        window.addEventListener('resize', () => {
            const activeDescriptionFields = document.querySelectorAll('.inventory-section-description-input');
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