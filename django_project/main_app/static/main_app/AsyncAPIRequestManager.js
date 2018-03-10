class AsyncAPIRequestManager {
  // Gives the user simple feedback on the progress of an
  // asynchronous API request. Also stops them from sending more
  // than one at a time.

  constructor() {
    this.apiCalls = {};
  }

  setAPICall(name, method, url, onLoadingStart, onLoadingDone,
    onLoadingFail) {
    // Once you start a request, onLoadingStart will be called.
    // After that, either onLoadingFail or onLoadingDone.
    this.apiCalls[name] = {
      name: name,
      method: method,
      url: url,
      onLoadingStart: onLoadingStart,
      onLoadingDone: onLoadingDone,
      onLoadingFail: onLoadingFail
    };
  }

  send(name) {
    // Send an API call with the given name.

    // Returns 0 if API call was sent. -1 if another
    // call is already in progress. -2 if call name not found.
    if (!this.apiCalls.hasOwnProperty(name)) {
      return -2;
    }

    var apiCall = this.apiCalls[name];
    var xhttp = new XMLHttpRequest();
    xhttp.open(apiCall.method, apiCall.url, true);

    if (this.currentlyBusy) {
      return -1;
    }

    this.currentlyBusy = true;
    apiCall.onLoadingStart();

    var this_ = this;

    xhttp.onload = function (info) {
      this_.currentlyBusy = false;

      if (xhttp.status === 200) {
        apiCall.onLoadingDone.apply(this, arguments);
      } else {
        apiCall.onLoadingFail.apply(this, arguments);
      }
    }

    xhttp.onerror = function () {
      this_.currentlyBusy = false;
      apiCall.onLoadingFail.apply(this, arguments);
    }

    xhttp.send();

    return 0;
  }
}
