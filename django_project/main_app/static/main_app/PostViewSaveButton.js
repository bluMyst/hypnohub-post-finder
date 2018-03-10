// Requires AsyncAPIRequestManager.js

var saveButton;
var saveManager = new AsyncAPIRequestManager();

function onSaveButtonClicked() {
    saveManager.send("save");
}

function resetSaveButton() {
    saveButton.innerHTML =  "<a href='#'>Click here to save votes.</a>";
    saveButton.onclick = onSaveButtonClicked;
}

function onSaveStart() {
    saveButton.innerText = "Saving...";
    saveButton.onclick = undefined;
}

function onSaveDone() {
    saveButton.innerText = "Done!";
    setTimeout(resetSaveButton, 2000);
}

function onSaveFail() {
    saveButton.innerText = "Failed.";
    setTimeout(resetSaveButton, 2000);
}

// TODO: Static /save URL
saveManager.setAPICall(
    "save",
    "GET", "/save",
    onSaveStart, onSaveDone, onSaveFail
);

window.addEventListener("load", function () {
    saveButton = document.getElementById("save_button");
    saveButton.onclick = onSaveButtonClicked;
    resetSaveButton();
});
