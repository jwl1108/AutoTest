chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SET_ACTIVE_URL") {
    chrome.storage.local.set({ activeUrl: message.url });
    sendResponse({ status: "stored" });
  }
});
