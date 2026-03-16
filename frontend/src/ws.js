/**
 * WebSocket client for Motif.
 */

export class MotifSocket {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.ws = null;
    this.handlers = {};
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this._stopped = false;
  }

  on(type, handler) {
    if (!this.handlers[type]) this.handlers[type] = [];
    this.handlers[type].push(handler);
    return this;
  }

  emit(type, data) {
    const fns = this.handlers[type] || [];
    fns.forEach((fn) => fn(data));
  }

  connect() {
    this._stopped = false;
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${location.host}/ws/${this.sessionId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.emit("connected");
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.emit(msg.type, msg);
      } catch (e) {
        console.error("Failed to parse message:", e);
      }
    };

    this.ws.onclose = () => {
      this.emit("disconnected");
      if (!this._stopped) {
        setTimeout(() => this.connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay
        );
      }
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
  }

  disconnect() {
    this._stopped = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(text) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "user_message", text }));
    }
  }
}
