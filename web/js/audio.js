/**
 * SoundManager —— 音效播放
 * 复用服务器 playsound 消息：content.sound 为 wav 文件名（无后缀）。
 * 音频文件直接引用项目根的 sounds/ 目录。
 */
class SoundManager {
  /**
   * @param {string} base 音频目录，默认项目根 sounds/
   */
  constructor(base = '../sounds/') {
    this.base = base;
    this.cache = new Map(); // name -> HTMLAudioElement
  }

  /**
   * 播放音效；同名音效并发时从头重播。
   * @param {string} name 音效名（如 'shotgun_shoot'）
   */
  play(name) {
    if (!name) return;
    let audio = this.cache.get(name);
    if (!audio) {
      audio = new Audio(this.base + name + '.wav');
      audio.preload = 'auto';
      this.cache.set(name, audio);
    }
    audio.currentTime = 0;
    const p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(() => { /* 浏览器自动播放策略下忽略 */ });
    }
  }
}
