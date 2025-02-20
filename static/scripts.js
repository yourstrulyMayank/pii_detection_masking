document.getElementById("file").addEventListener("change", function () {
    document.getElementById("file-name").textContent = this.files[0] ? this.files[0].name : "No file selected";
});

const fileTypeSelect = document.getElementById("file_type");
const checkboxesDiv = document.getElementById("checkboxes");

const labels = {
    "Document": ["Full Address", "Social Security Number", "Phone Number"],
    "Passport": ["Passport Number", "Date of Birth", "Nationality"],
    "PAN Card": ["PAN Number", "Full Name"],
    "Others": [],
    "Audio": ["Full Address", "Phone Number"]
};

fileTypeSelect.addEventListener("change", () => {
    checkboxesDiv.innerHTML = "";
    const selectedLabels = labels[fileTypeSelect.value] || [];
    
    selectedLabels.forEach(label => {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = "labels";
        checkbox.value = label;
        checkbox.id = label;

        const labelElement = document.createElement("label");
        labelElement.htmlFor = label;
        labelElement.textContent = label;

        checkboxesDiv.appendChild(checkbox);
        checkboxesDiv.appendChild(labelElement);
        checkboxesDiv.appendChild(document.createElement("br"));
    });
});
