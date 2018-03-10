var permalinkTextbox;
var permalinkUrl;
var copyPermalinkButton;

window.addEventListener("load", function () {
    permalinkTextbox    = document.getElementById("permalink_textbox");
    permalinkUrl        = permalinkTextbox.value;
    copyPermalinkButton = document.getElementById("copy_permalink");

    copyPermalinkButton.addEventListener("click", function () {
        permalinkTextbox.select();
        document.execCommand("copy");
    });
});
