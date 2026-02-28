window.addEventListener("load", () => {
    initializeUiBindings();

    document.body.addEventListener('htmx:afterSwap', (event) => {
        const target = event.target;
        if (!target || !target.id) {
            return;
        }

        if (target.id === 'classes-section-container') {
            selectClassField();
            bindClassLevelUpdateButtons();
            return;
        }

        if (target.id === 'feats-section-container') {
            selectFeatField();
            bindFeatDescriptionDisplayAutoHeight();
            return;
        }

        if (target.id === 'abilities-section-container') {
            bindProficiencyToggles();
            bindAbilitiesSectionLockToggle();
            return;
        }

        if (target.id === 'inventory-section-container') {
            selectInventoryField();
            bindInventoryDescriptionDisplayAutoHeight();
            return;
        }

        if (target.id === 'custom-stats-section-container') {
            selectCustomStatField();
            return;
        }

        if (target.id === 'custom-buffs-section-container') {
            selectCustomBuffField();
            bindProficiencyToggles();
            bindAbilitiesSectionLockToggle();
            bindCurrentHpCalculation();
            selectCustomStatField();
            decorateBuffedLabels();
        }
    });
})

let featDescriptionResizeWindowBound = false;
let inventoryDescriptionResizeWindowBound = false;
const ABILITY_LOCK_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365 * 5;

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

function initializeUiBindings() {
    selectClassField();
    selectFeatField();
    selectInventoryField();
    selectCustomStatField();
    selectCustomBuffField();
    bindClassLevelUpdateButtons();
    bindProficiencyToggles();
    bindAbilitiesSectionLockToggle();
    bindCurrentHpCalculation();
    bindFeatDescriptionDisplayAutoHeight();
    bindInventoryDescriptionDisplayAutoHeight();
    decorateBuffedLabels();
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

function selectCustomStatField() {
    const addCustomStatBtn = document.getElementById('add-custom-stat-btn');
    const addCustomStatBtnWrapper = document.getElementById('add-custom-stat-btn-wrapper');
    const addCustomStatFieldName = document.getElementById('add-custom-stat-field-name');
    const addCustomStatFieldValue = document.getElementById('add-custom-stat-field-value');
    const addCustomStatSubmitBtnWrapper = document.getElementById('add-custom-stat-submit-btn-wrapper');
    const closeCustomStatBtnWrapper = document.getElementById('close-custom-stat-btn-wrapper');
    const closeCustomStatFieldXBtn = document.getElementById('close-custom-stat-field-x-btn');

    if (!addCustomStatBtn || !addCustomStatBtnWrapper || !addCustomStatFieldName || !addCustomStatFieldValue || !addCustomStatSubmitBtnWrapper || !closeCustomStatBtnWrapper || !closeCustomStatFieldXBtn) {
        return;
    }

    addCustomStatBtn.addEventListener('click', () => {
        addCustomStatBtnWrapper.style.display = 'none';
        addCustomStatFieldName.style.display = 'flex';
        addCustomStatFieldValue.style.display = 'flex';
        addCustomStatSubmitBtnWrapper.style.display = 'flex';
        closeCustomStatBtnWrapper.style.display = 'flex';
    });

    closeCustomStatFieldXBtn.addEventListener('click', () => {
        addCustomStatBtnWrapper.style.display = 'flex';
        addCustomStatFieldName.style.display = 'none';
        addCustomStatFieldValue.style.display = 'none';
        addCustomStatSubmitBtnWrapper.style.display = 'none';
        closeCustomStatBtnWrapper.style.display = 'none';
    });
}

function selectClassField() {
    const addClassBtn = document.getElementById('add-class-btn');
    const closeClassFieldXBtn = document.getElementById('close-class-field-x-btn');
    const closeBtnWrapper = document.getElementById('close-class-btn-wrapper');
    const addClassFieldDropdown = document.getElementById('add-class-field-dropdown');
    const addClassFieldLevel = document.getElementById('add-class-field-level');
    const addClassSubmitBtn = document.getElementById('add-class-submit-btn');

    // Add null check to prevent errors if elements don't exist
    if (!addClassBtn || !closeClassFieldXBtn || !addClassFieldDropdown || !addClassFieldLevel || !closeBtnWrapper || !addClassSubmitBtn) {
        return;
    }

    addClassBtn.addEventListener("click", () => {
        // Hide the + button, show close button and input fields
        addClassBtn.parentElement.style.display = 'none';
        closeBtnWrapper.style.display = 'flex';
        addClassFieldDropdown.style.display = 'block';
        addClassFieldLevel.style.display = 'flex';
        addClassSubmitBtn.style.display = 'flex';
    });

    closeClassFieldXBtn.addEventListener("click", () => {
        // Show the + button, hide close button and input fields
        addClassBtn.parentElement.style.display = 'flex';
        closeBtnWrapper.style.display = 'none';
        addClassFieldDropdown.style.display = 'none';
        addClassFieldLevel.style.display = 'none';
        addClassSubmitBtn.style.display = 'none';
    });
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

    const parseNumberOrZero = (value) => {
        const parsed = Number.parseInt(value, 10);
        return Number.isNaN(parsed) ? 0 : parsed;
    };

    const getMaxCurrentHp = () => {
        const healthPoints = parseNumberOrZero(healthPointsField.value);
        const tempHp = parseNumberOrZero(tempHpField.value);
        return Math.max(0, healthPoints + tempHp);
    };

    let previousMaxCurrentHp = getMaxCurrentHp();

    const adjustCurrentHp = (delta) => {
        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxCurrentHp = getMaxCurrentHp();

        if (delta > 0) {
            currentHpField.value = Math.min(maxCurrentHp, currentHp + delta);
            return;
        }

        if (delta < 0) {
            if (currentHp <= 0) {
                currentHpField.value = 0;
                return;
            }

            const tempHp = parseNumberOrZero(tempHpField.value);
            if (tempHp > 0) {
                tempHpField.value = tempHp - 1;
            }

            currentHpField.value = Math.max(0, currentHp + delta);
        }
    };

    const calculateCurrentHp = () => {
        if (healthPointsField.value === '' && tempHpField.value === '') {
            currentHpField.value = '';
            previousMaxCurrentHp = 0;
            return;
        }

        const maxCurrentHp = getMaxCurrentHp();

        if (currentHpField.value === '') {
            currentHpField.value = maxCurrentHp;
            previousMaxCurrentHp = maxCurrentHp;
            return;
        }

        const currentHp = parseNumberOrZero(currentHpField.value);
        const maxDelta = maxCurrentHp - previousMaxCurrentHp;
        const adjustedCurrentHp = currentHp + maxDelta;

        currentHpField.value = Math.min(maxCurrentHp, Math.max(0, adjustedCurrentHp));
        previousMaxCurrentHp = maxCurrentHp;
    };

    healthPointsField.addEventListener('input', calculateCurrentHp);
    tempHpField.addEventListener('input', calculateCurrentHp);

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
    });

    calculateCurrentHp();
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