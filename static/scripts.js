document.getElementById("file").addEventListener("change", function () {
    document.getElementById("file-name").textContent = this.files[0] ? this.files[0].name : "No file selected";
});

const fileTypeSelect = document.getElementById("file_type");
const checkboxesDiv = document.getElementById("checkboxes");

// Updated labels based on new file type categories
const labels = {
    "PDF Document": ["Full Address", "Social Security Number", "Phone Number"],
    "Passport": ["Passport Number", "Date of Birth", "Nationality"],
    "Driving License": ["License Number", "Expiration Date", "Full Name"],
    "PAN Card": ["PAN Number", "Full Name"],
    "Local Card": ["ID Number", "Issuing Authority"],
    "Audio": ["Full Address", "Phone Number", "Speaker Identification"],
    "Excel File": ["Names", "Account Numbers", "Transaction Details"],
    "Database Extract": ["User IDs", "Emails", "Sensitive Data"]
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
