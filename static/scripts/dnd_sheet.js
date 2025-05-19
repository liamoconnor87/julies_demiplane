window.addEventListener("load", () => {
    selectClassField();
})

const addClassBtn = document.querySelector('.char-field-square-btn.add-class-btn');
const addClassBtnIcons = addClassBtn.querySelectorAll('i');
const classOptionsField = document.querySelector('.char-field-m.select-class-field');
const classLevelField = document.querySelector('.char-field-square.class-level-field');
const closeClassFieldXBtn = document.querySelector('.char-field-btn-del.close-class-field');

function selectClassField() {
    addClassBtn.addEventListener("click", () => {
        showHideClassField();
    });

    closeClassFieldXBtn.addEventListener("click", () => {
        showHideClassField();
    });

}

function showHideClassField() {
    // Ensure the fields exist before toggling classes
    if (classOptionsField && classLevelField) {
        classOptionsField.classList.toggle("display-none");
        classLevelField.classList.toggle("display-none");

        // Toggle visibility of icons inside the button
        addClassBtnIcons.forEach(icon => {
            icon.classList.toggle("display-none");
        });
    } else {
        console.error("Class options or level field not found.");
    }
}


const proficiencyFields = document.querySelectorAll('.proficient-hover');
proficiencyFields.forEach(field => {
    field.childNodes.forEach(child => {
        child.addEventListener("click", () => {
            field.classList.toggle("proficient-hl");
        });
    })
});