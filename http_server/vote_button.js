// I fucking hate Javascript so much

var doneLoading = false;
var canSave = false;
var saveButton;

window.onload = function () {
    saveButton = document.getElementById("save_button");

    saveButton.innerHTML = "<a href='#'>Click here to save votes.</a>"

    saveButton.onclick = function () {
        // So we don't setInterval multiple times
        if (canSave) { return; }
        canSave = true;

        saveButton.innerText = "Saving"

        var numDots = 0;
        var animationInterval = setInterval(function () {
            if (doneLoading) {
                clearInterval(animationInterval);
                saveButton.innerText = "Saved!";
                return;
            }

            if (numDots > 10) {
                saveButton.innerText = 'Saving';
                numDots = 0;
            } else {
                saveButton.innerText += '.';
                numDots++;
            }
        }, 250);

        var xhttp = new XMLHttpRequest();

        xhttp.onreadystatechange = function () {
            if (xhttp.readyState === XMLHttpRequest.DONE) {
                doneLoading = true;
            }
        }

        xhttp.open("GET", "/save", true);
        xhttp.send();
    }
}
