// It can't just be called "console" because that's already set to
// something else.
var outputConsole;
var updateTimeout = 1000;
var consoleId = new URL(location.href).searchParams.get("id");

function scrollToBottom() {
    outputConsole.scrollTop = outputConsole.scrollHeight;
}

function appendLines(lines) {
    if (lines === "") return;

    if (outputConsole.innerText === undefined ||
        outputConsole.innerText === "") {
        outputConsole.innerText = lines;
    } else {
        outputConsole.innerText += '\n' + lines;
    }

    scrollToBottom();
}

function checkForUpdate() {
    var xhttp = new XMLHttpRequest();
    var url;

    //var firstUpdate = (
    //  outputConsole.innerText === undefined ||
    //  outputConsole.innerText === "");

    xhttp.onreadystatechange = function () {
        if (xhttp.readyState === XMLHttpRequest.DONE) {
            var stopPolling = false;
            var response = JSON.parse(xhttp.responseText);
            console.log(response);

            if (response.indexOf(null) !== -1) {
                if (response.indexOf(null) === response.length-1) {
                    stopPolling = true;
                    response.pop();
                } else {
                    appendLines(
                        "Clientside error: Recieved response with null, but not at the end.");
                    response = [];
                }
            }

            appendLines(response.join('\n'));

            if (!stopPolling) {
                setTimeout(checkForUpdate, updateTimeout);
            }
        }
    }

    //if (firstUpdate) {
    //  url = "/readConsole?id=" + consoleId + "&readAll=true";
    //} else {
    //  url = "/readConsole?id=" + consoleId;
    //}
    url = "/readConsole?id=" + consoleId;

    xhttp.open("GET", url, true);
    xhttp.send();
}

window.onload = function() {
    outputConsole = document.getElementById("console");

    if (consoleId === null) {
        appendLines("Error: No consoleId found in URL's query string.");
        return;
    }

    checkForUpdate();
}
