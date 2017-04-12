// Designed to be used in /vote to get the upvote and downvote actions to work.
// Remember to send this script a post_id so it knows what it's voting on.

var has_voted = false

function vote(direction) {
    // direction == true: upvote
    // direction == false: downvote
    if (!has_voted) {
        var confirmation = confirm(
            "Want to "
            + (direction ? 'upvote' : 'downvote')
            + " the current image?"
        )

        var fail_handler = function () {
            alert("Vote request failed. See console for details.")
            console.log("Vote request failed. Args:")
            console.log(arguments)
        }

        if (!confirmation) { return }

        var oReq = new XMLHttpRequest()

        oReq.addEventListener("load", function(oEvent)  {
            // has_voted is useless unless you comment out location.reload()
            has_voted = true
            location.reload()
        })

        oReq.addEventListener("error", fail_handler)
        oReq.addEventListener("abort", fail_handler)

        oReq.open("GET", "/vote"
            + "?direction=" + direction.toString()
            + "&id=" + post_id.toString()
        )

        oReq.send()
    }
}

function upvote()   {vote(true)}
function downvote() {vote(false)}

document.addEventListener('keyup', function(event) {
    if (event.key === 'a') {
        upvote()
    } else if (event.key === 'z') {
        downvote()
    }
})
