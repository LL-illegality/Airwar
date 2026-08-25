/**
 * NetClient —— WebSocket 封装
 * 复用桌面客户端与服务器之间的消息协议：
 *   客户端发送: connect / keyDown / keyUp / joyAxis / joyHat / disconnect
 *   服务器推送: connect / screen_info / game_state_changed / playsound /
 *              load_level / set_title / particle_effect
 * 注意：服务器使用 eval 解析消息（Python 表达式），因此这里发送的 JSON
 * 中不能出现 true/false/null 字面量，一律使用字符串或数字。
 */
class NetClient {
  /**
   * @param {string} url ws://或wss://地址
   * @param {(msg: {sender: string, type: string, content: any}) => void} onMessage
   * @param {(status: string) => void} onStatus 连接状态回调（'connecting'|'connected'|'reconnecting'）
   */
  constructor(url, onMessage, onStatus) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
    this.playerId = -1;
    this.playerName = '';
    this.ws = null;
    this.closed = false;      // 主动关闭标记（退出时置 true，停止重连）
    this.reconnectDelay = 3000;
    this._reconnectTimer = null;
    // 页面关闭/刷新时通知服务器移除玩家（对齐桌面端 disconnect 协议）。
    // 即使此消息丢失，服务器端也已修复 async for 正常关闭的清理路径（双保险）。
    window.addEventListener('beforeunload', () => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ sender: String(this.playerId), type: 'disconnect', content: {} }));
        } catch (e) { /* 忽略 */ }
      }
    });
  }

  /** 建立连接；连接成功后自动发送 connect 消息注册玩家。 */
  connect(playerName) {
    this.playerName = playerName;
    this.closed = false;
    this._open();
  }

  _open() {
    this.onStatus('connecting');
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this._scheduleReconnect();
      return;
    }
    this.ws.onopen = () => {
      this.onStatus('connected');
      // 注册玩家；sender 在连接前固定为 0（服务器忽略 sender，返回真实 id）
      this._sendRaw({ sender: '0', type: 'connect', content: { playerName: this.playerName } });
    };
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg && msg.type === 'connect' && msg.content && typeof msg.content.player_id === 'number') {
          this.playerId = msg.content.player_id;
        }
        this.onMessage(msg);
      } catch (e) {
        console.warn('无法解析服务器消息:', ev.data, e);
      }
    };
    this.ws.onclose = () => {
      this.onStatus('reconnecting');
      if (!this.closed) this._scheduleReconnect();
    };
    this.ws.onerror = () => {
      // onclose 会随后触发
    };
  }

  _scheduleReconnect() {
    if (this.closed) return;
    clearTimeout(this._reconnectTimer);
    this._reconnectTimer = setTimeout(() => this._open(), this.reconnectDelay);
  }

  /** 发送业务消息（type + content）。 */
  send(type, content) {
    this._sendRaw({ sender: String(this.playerId), type, content });
  }

  _sendRaw(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  /** 主动断开（不再重连）。 */
  disconnect() {
    this.closed = true;
    clearTimeout(this._reconnectTimer);
    if (this.ws) {
      try { this.ws.close(); } catch (e) { /* ignore */ }
    }
  }
}
