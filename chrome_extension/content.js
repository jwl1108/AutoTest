document.addEventListener("click", function(e) {
  const elementInfo = {
    tag: e.target.tagName,
    id: e.target.id,
    class: e.target.className,
    text: e.target.innerText,
  };

  fetch("http://localhost:5000/click", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(elementInfo)
  });
});
