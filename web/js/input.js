/**
 * InputManager —— 键盘 + 触屏虚拟摇杆 + 触屏按钮
 * 键码与桌面端 pygame.K_* 保持一致（服务器 Keys 枚举）：
 *   w=119 s=115 a=97 d=100 c=99 e=101 p=112 space=32 z=122
 * 触屏摇杆映射为 joyAxis 消息（axis=0 水平 / axis=1 垂直）。
 */
class InputManager {
  /**
   * @param {NetClient} net
   * @param {HTMLCanvasElement} canvas
   * @param {SoundManager} sound 本地音效（准备/取消准备，对齐桌面端本地播放）
   */
  constructor(net, canvas, sound) {
    this.net = net;
    this.sound = sound;
    this.pressedKeys = new Set(); // 已发送 keyDown 的键码，防止重复
    this._setupKeyboard();
    this._setupTouch();
  }

  /** 浏览器键码 -> 游戏键码（pygame.K_*） */
  static KEY_MAP = {
    87: 119,  // W -> w
    38: 119,  // ArrowUp -> w
    83: 115,  // S -> s
    40: 115,  // ArrowDown -> s
    65: 97,   // A -> a
    37: 97,   // ArrowLeft -> a
    68: 100,  // D -> d
    39: 100,  // ArrowRight -> d
    32: 32,   // Space
    67: 99,   // C -> c
    69: 101,  // E -> e
    90: 122,  // Z -> z
    80: 112,  // P -> p
  };

  _setupKeyboard() {
    window.addEventListener('keydown', (e) => {
      const key = InputManager.KEY_MAP[e.keyCode];
      if (key === undefined) return;
      e.preventDefault();
      if (key === 99) this.sound.play('prepare'); // C 按下：对齐桌面端本地播放
      if (!this.pressedKeys.has(key)) {
        this.pressedKeys.add(key);
        this.net.send('keyDown', { key });
      }
    });
    window.addEventListener('keyup', (e) => {
      const key = InputManager.KEY_MAP[e.keyCode];
      if (key === undefined) return;
      e.preventDefault();
      if (key === 99) this.sound.play('unprepare'); // C 松开
      if (this.pressedKeys.has(key)) {
        this.pressedKeys.delete(key);
        this.net.send('keyUp', { key });
      }
    });
    // 切出页面时释放所有按键，避免卡键
    window.addEventListener('blur', () => {
      for (const key of this.pressedKeys) this.net.send('keyUp', { key });
      this.pressedKeys.clear();
    });
  }

  _setupTouch() {
    const zone = document.getElementById('joystickZone');
    const base = document.getElementById('joystickBase');
    const knob = document.getElementById('joystickKnob');
    const MAX_RADIUS = 56;
    let active = false;
    let centerX = 0;
    let centerY = 0;

    // 阻止移动端长按选中文字/弹出系统菜单（contextmenu/selectstart），
    // 这些系统行为会接管触摸导致 pointercancel → 断触
    const blockLongPress = (e) => e.preventDefault();
    zone.addEventListener('contextmenu', blockLongPress);
    zone.addEventListener('selectstart', blockLongPress);
    // 关键：touchstart/touchmove 非 passive preventDefault——
    // iOS Safari 长按文本选择/呼出、Android 长按菜单与滚动均被阻止，
    // 这是比 user-select/CSS 更可靠的断触防护（Pointer Events 不受其影响）
    const blockTouch = (e) => e.preventDefault();
    zone.addEventListener('touchstart', blockTouch, { passive: false });
    zone.addEventListener('touchmove', blockTouch, { passive: false });
    // 兜底：整个触屏控件容器（含按钮面板与中间空白区）都禁止长按系统行为
    const controls = document.getElementById('touchControls');
    if (controls) {
      controls.addEventListener('contextmenu', blockLongPress);
      controls.addEventListener('selectstart', blockLongPress);
      controls.addEventListener('touchstart', blockTouch, { passive: false });
      controls.addEventListener('touchmove', blockTouch, { passive: false });
    }

    const setAxis = (dx, dy) => {
      const len = Math.hypot(dx, dy);
      const clamp = len > MAX_RADIUS ? MAX_RADIUS / len : 1;
      const vx = dx * clamp / MAX_RADIUS;
      const vy = dy * clamp / MAX_RADIUS;
      this.net.send('joyAxis', { axis: 0, value: Math.round(vx * 100) / 100 });
      this.net.send('joyAxis', { axis: 1, value: Math.round(vy * 100) / 100 });
      knob.style.transform = `translate(calc(-50% + ${dx * clamp}px), calc(-50% + ${dy * clamp}px))`;
    };

    zone.addEventListener('pointerdown', (e) => {
      active = true;
      centerX = e.clientX;
      centerY = e.clientY;
      // 指针捕获：按住期间手指微移滑出区域边界也不会触发 leave/cancel 类断触
      if (zone.setPointerCapture) {
        try { zone.setPointerCapture(e.pointerId); } catch (err) { /* 忽略 */ }
      }
      base.classList.remove('hidden');
      base.style.left = centerX + 'px';
      base.style.top = centerY + 'px';
      knob.style.transform = 'translate(-50%, -50%)';
    });
    zone.addEventListener('pointermove', (e) => {
      if (!active) return;
      setAxis(e.clientX - centerX, e.clientY - centerY);
    });
    const endJoy = () => {
      if (!active) return;
      active = false;
      base.classList.add('hidden');
      this.net.send('joyAxis', { axis: 0, value: 0 });
      this.net.send('joyAxis', { axis: 1, value: 0 });
    };
    zone.addEventListener('pointerup', endJoy);
    zone.addEventListener('pointercancel', endJoy);

    // 触屏按钮：按下发送 keyDown，松开发送 keyUp
    const buttons = document.querySelectorAll('.btn');
    for (const btn of buttons) {
      const key = Number(btn.dataset.key);
      btn.addEventListener('contextmenu', blockLongPress);
      btn.addEventListener('selectstart', blockLongPress);
      const press = (e) => {
        e.preventDefault();
        btn.classList.add('active');
        // 指针捕获：长按期间手指自然微移滑出按钮边界也不会触发 pointerleave 断触
        if (btn.setPointerCapture) {
          try { btn.setPointerCapture(e.pointerId); } catch (err) { /* 忽略 */ }
        }
        if (key === 99) this.sound.play('prepare'); // 准备按钮按下
        if (!this.pressedKeys.has(key)) {
          this.pressedKeys.add(key);
          this.net.send('keyDown', { key });
        }
      };
      const release = () => {
        btn.classList.remove('active');
        if (key === 99) this.sound.play('unprepare'); // 准备按钮松开
        if (this.pressedKeys.has(key)) {
          this.pressedKeys.delete(key);
          this.net.send('keyUp', { key });
        }
      };
      btn.addEventListener('pointerdown', press);
      btn.addEventListener('pointerup', release);
      btn.addEventListener('pointercancel', release);
      // 保留 pointerleave：无 setPointerCapture 支持的旧浏览器兜底
      btn.addEventListener('pointerleave', release);
      // 长按按钮文字/呼出系统菜单会触发 pointercancel 断触，必须阻止原生触摸行为
      btn.addEventListener('touchstart', blockTouch, { passive: false });
      btn.addEventListener('touchmove', blockTouch, { passive: false });
    }
  }
}
