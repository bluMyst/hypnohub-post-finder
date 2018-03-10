// Requires AsyncAPIRequestManager.js

// Remember to set postId somewhere in the HTML, or this file won't know what
// we're voting on.

var upvoteButton;
var downvoteButton;
var voteManager = new AsyncAPIRequestManager();

function setVoteButtonClass(direction, class_) {
    var dirBtn = direction ? upvoteButton : downvoteButton;
    dirBtn.classList.remove("inactive");
    dirBtn.classList.remove("loading");
    dirBtn.classList.remove("active");
    dirBtn.classList.add(class_);
}

function onVoteStart(direction) {
    return function () {
        setVoteButtonClass(direction, "loading");
    }
}

function onVoteDone(direction) {
    return function () {
        setVoteButtonClass(direction,  "active");
        setVoteButtonClass(!direction, "inactive");
    }
}

function onVoteFail(direction) {
    return function () {
        setVoteButtonClass(direction, "inactive");
    }
}

// TODO: Static /vote URL
voteManager.setAPICall(
    "upvote",
    "GET", "/vote?up=true&id=" + postId,
    onVoteStart(true), onVoteDone(true), onVoteFail(true)
);

voteManager.setAPICall(
    "downvote",
    "GET", "/vote?up=false&id=" + postId,
    onVoteStart(false), onVoteDone(false), onVoteFail(false)
);

function upvote() { voteManager.send("upvote"); }
function downvote() { voteManager.send("downvote"); }

document.addEventListener('keyup', function(event) {
    if (event.key === 'a') {
        upvote();
    } else if (event.key === 'z') {
        downvote();
    }
});

window.addEventListener("load", function () {
    upvoteButton   = document.getElementsByClassName('upvote')[0];
    downvoteButton = document.getElementsByClassName('downvote')[0];

    upvoteButton.addEventListener("click", upvote);
    downvoteButton.addEventListener("click", downvote);
});
