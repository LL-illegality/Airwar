/**
 * MusicManager —— 背景音乐（复刻桌面端 MusicLoader 三态逻辑）
 * 监听 game_state_changed：
 *   mainMenu(0)  → mainmenu.wav 循环
 *   loadLevel(1) → 随机选一首 intro 循环（future/lostcity/pop/universe41/beach/escape）
 *   inGame(2)    → 切到已选 intro 对应的 loop 曲（桌面 introLoopMap 语义）
 * 其他状态不切换音乐（与桌面一致）。Web 端无教程，不处理 tutorial.wav。
 * 注意：浏览器自动播放策略要求首次播放由用户手势触发（"加入游戏"按钮点击满足）。
 */
class MusicManager {
  static INTROS = ['future', 'lostcity', 'pop', 'universe41', 'beach', 'escape'];

  /**
   * @param {string} base 音乐目录，默认项目根 music/
   */
  constructor(base = '../music/') {
    this.base = base;
    this.audio = null;      // 当前 Audio 元素
    this.playingName = '';  // 当前播放的文件名（无后缀）
    this.currIntro = null;  // 当前 intro 曲名（对应 loop 曲名）
    this.historyState = -1; // 上次处理的游戏状态
    this._pending = false;  // play() 被自动播放策略拒绝，等待用户手势解锁
    // 浏览器自动播放策略：Audio.play() 必须在用户手势中（或之后）才能发声。
    // 加入按钮点击后连接服务器、收到状态消息时已不在手势上下文 → play() 被拒。
    // 监听用户后续手势（点击/按键/触摸）解锁重试。
    this._onGesture = () => this._unlock();
    document.addEventListener('pointerdown', this._onGesture);
    document.addEventListener('keydown', this._onGesture);
    document.addEventListener('touchstart', this._onGesture);
  }

  /** 用户手势触发时恢复被自动播放策略挂起的音乐 */
  _unlock() {
    if (this.audio && this.audio.paused && this.playingName) {
      const p = this.audio.play();
      if (p && typeof p.catch === 'function') p.catch(() => {});
    }
    this._pending = false;
  }

  /**
   * @param {number} state GameState 值
   */
  onGameStateChanged(state) {
    if (state === this.historyState) return;
    this.historyState = state;
    if (state === 0) {
      this._play('mainmenu', true);
    } else if (state === 1) {
      this.currIntro = MusicManager.INTROS[Math.floor(Math.random() * MusicManager.INTROS.length)];
      this._play(this.currIntro + '_intro', true);
    } else if (state === 2) {
      if (this.currIntro) {
        this._play(this.currIntro, true); // loop 曲名 = intro 曲名
      }
    }
  }

  /**
   * @param {string} name 音乐文件名（无后缀）
   * @param {boolean} loop 是否循环
   */
  _play(name, loop) {
    if (this.playingName === name) return;
    this._stop();
    const audio = new Audio(this.base + name + '.wav');
    audio.loop = loop;
    const p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => {
        // 自动播放策略拒绝：保留音频元素，等待用户手势 _unlock() 重试
        this._pending = true;
      });
    }
    this.audio = audio;
    this.playingName = name;
  }

  _stop() {
    if (this.audio) {
      this.audio.pause();
      this.audio.currentTime = 0;
      this.audio = null;
    }
    this.playingName = '';
  }
}
