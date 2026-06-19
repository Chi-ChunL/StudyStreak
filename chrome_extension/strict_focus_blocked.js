const params = new URLSearchParams(window.location.search);
const redirectUrl = params.get("redirect") || "about:blank";
const subject = params.get("subject") || "your focus session";
const message = document.querySelector("#message");
const openLink = document.querySelector("#open-link");

message.textContent = `You are focusing on ${subject}. This page is outside your allowed websites.`;
openLink.href = redirectUrl;

setTimeout(() => {
    window.location.href = redirectUrl;
}, 1200);
