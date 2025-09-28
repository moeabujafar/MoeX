console.log("✅ app.js loaded");

async function sendMessage() {
  const input = document.getElementById("userInput").value;
  const res = await fetch("https://moex-api.onrender.com/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: input }),
  });
  const data = await res.json();
  document.getElementById("chat").innerText = data.reply || "(no reply)";
}
