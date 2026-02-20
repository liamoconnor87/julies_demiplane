window.addEventListener("load", () => {
    selectClassField();
    bindClassLevelUpdateButtons();
    bindProficiencyToggles();
    bindCurrentHpCalculation();
})

const addClassBtn = document.getElementById('add-class-btn');
const closeClassFieldXBtn = document.getElementById('close-class-field-x-btn');
const closeBtnWrapper = document.getElementById('close-class-btn-wrapper');
const addClassFieldDropdown = document.getElementById('add-class-field-dropdown');
const addClassFieldLevel = document.getElementById('add-class-field-level');
const addClassSubmitBtn = document.getElementById('add-class-submit-btn');

function selectClassField() {
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

function bindClassLevelUpdateButtons() {
    const classLevelInputs = document.querySelectorAll('.class-level-input');

    classLevelInputs.forEach((input) => {
        const classId = input.dataset.charClassId;
        const actionBtn = document.getElementById(`classes-action-${classId}`);
        const actionLabel = document.getElementById(`classes-action-label-${classId}`);

        if (!actionBtn || !actionLabel) {
            return;
        }

        const removeUrl = actionBtn.dataset.removeUrl;

        const setButtonMode = () => {
            const currentValue = input.value.trim();
            const originalValue = (input.dataset.originalValue || '').trim();
            const hasChanged = currentValue !== originalValue;

            if (hasChanged) {
                actionBtn.type = 'submit';
                actionBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
                actionLabel.textContent = 'Update';
                actionBtn.onclick = null;
                return;
            }

            actionBtn.type = 'button';
            actionBtn.textContent = '−';
            actionLabel.textContent = 'Remove';
            actionBtn.onclick = () => {
                window.location.href = removeUrl;
            };
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

            if (wasChecked && !checkbox.checked) {
                item.classList.add('toggle-border-suppressed');
                window.setTimeout(() => {
                    item.classList.remove('toggle-border-suppressed');
                }, 180);
            }
        };

        item.addEventListener('click', () => {
            toggleCheckbox();
        });

        item.addEventListener('keydown', (event) => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                toggleCheckbox();
            }
        });

        syncVisualState();
    });
}