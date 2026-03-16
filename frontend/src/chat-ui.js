/**
 * Chat UI — message rendering and input handling.
 */

export class ChatUI {
  constructor(getSocket) {
    // getSocket can be a function that returns the current socket, or a socket instance
    this._getSocket = typeof getSocket === "function" ? getSocket : () => getSocket;
    this.messages = document.getElementById("chat-messages");
    this.input = document.getElementById("chat-input");
    this.sendBtn = document.getElementById("send-btn");
    this.currentAgentMsg = null;

    this.setupInput();
  }

  setupInput() {
    const send = () => {
      const text = this.input.value.trim();
      if (!text) return;

      this.addUserMessage(text);
      const socket = this._getSocket();
      if (socket) socket.send(text);
      this.input.value = "";
      this.input.focus();
    };

    this.sendBtn.addEventListener("click", send);
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
  }

  clearMessages() {
    this.messages.innerHTML = "";
    this.currentAgentMsg = null;
  }

  loadHistory(messages) {
    for (const msg of messages) {
      const el = document.createElement("div");
      if (msg.role === "user") {
        el.className = "message user";
        el.textContent = msg.text;
      } else {
        el.className = "message agent";
        el.textContent = msg.text;
      }
      this.messages.appendChild(el);
    }
    this.scrollToBottom();
  }

  addUserMessage(text) {
    const el = document.createElement("div");
    el.className = "message user";
    el.textContent = text;
    this.messages.appendChild(el);
    this.scrollToBottom();
  }

  appendAgentText(text, done) {
    if (!this.currentAgentMsg) {
      this.currentAgentMsg = document.createElement("div");
      this.currentAgentMsg.className = "message agent";
      this.currentAgentMsg.innerHTML = '<span class="content"></span><span class="cursor"></span>';
      this.messages.appendChild(this.currentAgentMsg);
    }

    const content = this.currentAgentMsg.querySelector(".content");
    content.textContent += text;

    if (done) {
      const cursor = this.currentAgentMsg.querySelector(".cursor");
      if (cursor) cursor.remove();
      this.currentAgentMsg = null;
    }

    this.scrollToBottom();
  }

  addAnimationMessage(name, color) {
    const el = document.createElement("div");
    el.className = "message animation-unlock";
    el.innerHTML = `
      <div class="animation-unlock-glow" style="--unlock-color: ${color}"></div>
      <div class="animation-unlock-content">
        <span class="animation-unlock-icon">✦</span>
        <span class="animation-unlock-text">New Animation Unlocked</span>
        <span class="animation-unlock-name" style="color: ${color}">${name}</span>
      </div>
    `;
    this.messages.appendChild(el);
    this.scrollToBottom();
  }

  scrollToBottom() {
    this.messages.scrollTop = this.messages.scrollHeight;
  }
}
