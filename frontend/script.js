const API_URL = "http://localhost:8000";
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const dropZone = document.getElementById("dropZone");
const uploadStatus = document.getElementById("uploadStatus");
const kbStats = document.getElementById("kbStats");
const filesList = document.getElementById("filesList");
const clearKBBtn = document.getElementById("clearKBBtn");

function addMessage(text, type, sources = []) {
  const div = document.createElement("div");
  div.className = `message ${type}`;
  div.textContent = text;
  
  if (sources.length > 0) {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "message-sources";
    sourcesDiv.textContent = `Sources: ${sources.join(", ")}`;
    div.appendChild(sourcesDiv);
  }
  
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function updateKBStats() {
  try {
    const response = await fetch(`${API_URL}/knowledge-base`);
    const data = await response.json();
    
    kbStats.innerHTML = `
      <p><strong>Total Chunks:</strong> ${data.total_chunks}</p>
      <p><strong>Files:</strong> ${data.files_indexed}</p>
    `;
  } catch (error) {
    kbStats.innerHTML = "<p>Error loading stats</p>";
  }
}

async function updateFilesList() {
  try {
    const response = await fetch(`${API_URL}/files-indexed`);
    const data = await response.json();
    
    if (data.count === 0) {
      filesList.innerHTML = '<p style="color: #94a3b8; font-size: 0.9rem;">No files indexed</p>';
    } else {
      filesList.innerHTML = data.files.map(f => `<div class="file-item">📄 ${f}</div>`).join("");
    }
  } catch (error) {
    filesList.innerHTML = "<p>Error loading files</p>";
  }
}

updateKBStats();
updateFilesList();

uploadBtn.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", async (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  await uploadFiles(files);
});

fileInput.addEventListener("change", async () => {
  await uploadFiles(fileInput.files);
  fileInput.value = "";
});

async function uploadFiles(files) {
  if (files.length === 0) return;

  uploadStatus.textContent = `Uploading ${files.length} file(s)...`;
  
  for (const file of files) {
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
      });
      
      const data = await response.json();
      
      if (response.ok) {
        uploadStatus.textContent = `✓ ${file.name} uploaded successfully`;
        uploadStatus.style.color = "#4ade80";
        
        setTimeout(() => {
          updateKBStats();
          updateFilesList();
          uploadStatus.textContent = "";
        }, 1000);
      } else {
        uploadStatus.textContent = `✗ Error: ${data.detail}`;
        uploadStatus.style.color = "#ef4444";
      }
    } catch (error) {
      uploadStatus.textContent = `✗ Upload failed: ${error.message}`;
      uploadStatus.style.color = "#ef4444";
    }
  }
}

clearKBBtn.addEventListener("click", async () => {
  if (confirm("Are you sure? This will delete all indexed documents.")) {
    try {
      const response = await fetch(`${API_URL}/knowledge-base`, {
        method: "DELETE"
      });
      const data = await response.json();
      uploadStatus.textContent = "Knowledge base cleared";
      uploadStatus.style.color = "#fbbf24";
      
      setTimeout(() => {
        updateKBStats();
        updateFilesList();
        uploadStatus.textContent = "";
      }, 1000);
    } catch (error) {
      uploadStatus.textContent = `Error: ${error.message}`;
      uploadStatus.style.color = "#ef4444";
    }
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = userInput.value.trim();
  if (!question) return;

  addMessage(question, "user");
  userInput.value = "";
  addMessage("Thinking...", "bot");

  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message: question })
    });

    const data = await response.json();
    const botMessages = document.querySelectorAll(".message.bot");
    const lastBot = botMessages[botMessages.length - 1];

    if (lastBot && lastBot.textContent === "Thinking...") {
      lastBot.remove();
      addMessage(data.reply || "Sorry, I couldn't find an answer.", "bot", data.sources || []);
    }
  } catch (error) {
    const botMessages = document.querySelectorAll(".message.bot");
    const lastBot = botMessages[botMessages.length - 1];
    if (lastBot && lastBot.textContent === "Thinking...") {
      lastBot.textContent = `Connection error: ${error.message}`;
    }
  }
});
