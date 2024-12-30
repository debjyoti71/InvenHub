// Copy Button Logic
document.getElementById("copy-btn").addEventListener("click", function () {
    const button = this; // Reference the button
    const storeId = document.querySelector(".storeId").textContent.trim(); // Trim whitespace

    navigator.clipboard.writeText(storeId)
        .then(() => {
            button.textContent = "Copied!"; // Change button text
            button.style.backgroundColor = "var(--600)"; // Change background to green
            button.style.color = "white"; // Ensure text remains visible

            setTimeout(() => {
                button.textContent = "Copy"; // Revert text
                button.style.backgroundColor = "var(--100)"; // Revert background to blue
                button.style.color = "black"; // Reset text color
            }, 2000);
        })
        .catch(err => alert("Failed to copy: " + err));
});

// Make Editable
function makeEditable() {
    const editableDivs = document.querySelectorAll(".editable");
    editableDivs.forEach(function(div) {
        div.contentEditable = true;
        div.style.border = "0.5px solid black";
    });

    document.getElementById('editButton').style.visibility = "hidden";
    document.getElementById('saveButton').style.visibility = "visible";
    document.getElementById('profile-label').style.display = "flex";
}

// Make Non-Editable and Post Data
function makeNonEditable() {
    const editableDivs = document.querySelectorAll(".editable");
    const updatedData = new FormData(); // Use FormData to handle file uploads and text data

    editableDivs.forEach(function(div) {
        div.contentEditable = false;
        div.style.border = "unset";

        // Get label (if exists) or ID to form data keys
        const label = div.previousElementSibling ? div.previousElementSibling.textContent.trim() : div.id;
        updatedData.append(label.toLowerCase().replace(/\s/g, "_"), div.textContent.trim());
    });

    // Add user_id to the data
    const user_id = document.getElementById('userinput').value;
    updatedData.append("user_id", user_id);

    // Add profile picture if a new file is uploaded
    const fileInput = document.getElementById("file-input");
    if (fileInput.files.length > 0) {
        updatedData.append("profile_picture", fileInput.files[0]);
    }

    // Post the data to the server
    fetch('/account', {
        method: 'POST',
        body: updatedData, // Send the FormData object
    })
    .then(response => {
        if (response.ok) {
            alert("Profile updated successfully!");
        } else {
            alert("Failed to update profile.");
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred while saving.");
    });

    document.getElementById('editButton').style.visibility = "visible";
    document.getElementById('saveButton').style.visibility = "hidden";
    document.getElementById('profile-label').style.display = "none";
}

// Profile image preview
var fileInput = document.getElementById('file-input');
var image = document.getElementById('profile-image');

fileInput.onchange = function() {
    var source = URL.createObjectURL(fileInput.files[0]);
    image.style.backgroundImage = `url(${source})`;
};
