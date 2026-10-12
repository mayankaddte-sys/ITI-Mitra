const API_URL = window.ITI_MITRA_API_URL || "";
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const chatBox = document.getElementById("chatBox");
const chips = document.getElementById("chips");

const history = []; // [{role, content}] kept in the browser only; the server stores nothing

const QUICK_QUESTIONS = [
  ["प्रवेश / Admission", "आईटीआई में प्रवेश के लिए पात्रता क्या है?"],
  ["परीक्षा / Exam", "Exam schedule and exam pattern kya hai?"],
  ["छात्रवृत्ति / Scholarship", "कौन-कौन सी छात्रवृत्तियाँ उपलब्ध हैं?"],
  ["Apprenticeship", "How can I apply for apprenticeship?"],
  ["नौकरी / Jobs", "आईटीआई के बाद नौकरी और प्लेसमेंट के अवसर क्या हैं?"],
];

function addMessage(text, type, sources = []) {
  const div = document.createElement("div");
  div.className = `message ${type}`;
  div.textContent = text; // never innerHTML: model output / filenames are untrusted
  div.style.whiteSpace = "pre-wrap";
  if (sources.length) {
    const s = document.createElement("div");
    s.className = "message-sources";
    s.textContent = `Sources / स्रोत: ${sources.join(", ")}`;
    div.appendChild(s);
  }
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
  return div;
}

function addFeedback(messageDiv, question, reply) {
  const row = document.createElement("div");
  row.className = "feedback";
  const label = document.createElement("span");
  label.textContent = "क्या यह उत्तर उपयोगी था? / Helpful? ";
  row.appendChild(label);
  ["up", "down"].forEach((rating) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = rating === "up" ? "👍" : "👎";
    b.addEventListener("click", async () => {
      row.querySelectorAll("button").forEach((x) => (x.disabled = true));
      label.textContent = "धन्यवाद! / Thanks! ";
      try {
        await fetch(`${API_URL}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating, question, reply }),
        });
      } catch (e) { /* feedback is best-effort */ }
    });
    row.appendChild(b);
  });
  messageDiv.appendChild(row);
}

async function ask(question) {
  addMessage(question, "user");
  const thinking = addMessage("सोच रहा हूँ… / Thinking…", "bot");
  sendBtn.disabled = true;
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, history: history.slice(-6) }),
    });
    const data = await response.json().catch(() => ({}));
    thinking.remove();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "Something went wrong. Please try again.";
      addMessage(detail, "bot");
      return;
    }
    const botDiv = addMessage(data.reply || "Sorry, I couldn't find an answer.", "bot", data.sources || []);
    if ((data.sources || []).length) addFeedback(botDiv, question, data.reply || "");
    history.push({ role: "user", content: question }, { role: "assistant", content: data.reply || "" });
    if (history.length > 12) history.splice(0, history.length - 12);
  } catch (err) {
    thinking.remove();
    addMessage("Connection error. Please check your internet and try again. / कनेक्शन त्रुटि।", "bot");
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = userInput.value.trim();
  if (!q) return;
  userInput.value = "";
  ask(q);
});

QUICK_QUESTIONS.forEach(([label, question]) => {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "chip";
  b.textContent = label;
  b.addEventListener("click", () => ask(question));
  chips.appendChild(b);
});
