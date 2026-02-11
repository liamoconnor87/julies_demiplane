window.addEventListener("load", () => {
    selectClassField();
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

// Function to update inventory item quantity
function updateInventoryItem(itemId) {
    const qtyInput = document.getElementById('inventory-quantity-' + itemId);
    const newQuantity = qtyInput.value;

    // You can implement this as a fetch request or form submission
    // For now, this will trigger the main form save
    alert('Update inventory quantity to ' + newQuantity + ' - Click Save at the bottom to persist changes');
}


const proficiencyFields = document.querySelectorAll('.proficient-hover');
proficiencyFields.forEach(field => {
    field.childNodes.forEach(child => {
        child.addEventListener("click", () => {
            field.classList.toggle("proficient-hl");
        });
    })
});