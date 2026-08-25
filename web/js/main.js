/**
 * main.js —— 入口：连接流程、消息分发、游戏循环
 * 消息分发对应桌面端 ResourcesLoader.processMappingTable。
 */
(() => {
  'use strict';

  const lobby = document.getElementById('lobby');
  const gameDiv = document.getElementById('game');
  const canvas = document.getElementById('gameCanvas');
  const serverInput = document.getElementById('serverInput');
  const nameInput = document.getElementById('nameInput');
  const joinBtn = document.getElementById('joinBtn');
  const statusText = document.getElementById('statusText');
  const touchControls = document.getElementById('touchControls');

  // ========== 默认值 ==========
  const params = new URLSearchParams(window.location.search);
  const host = window.location.hostname || '127.0.0.1'; // file:// 打开时回退
  const fallbackServer = params.get('server') || 'ws://' + host + ':8000';
  serverInput.value = fallbackServer;
  nameInput.value = params.get('name') || '';

  // 优先从 Flask 的 /api/config 获取默认服务器地址（P1-3）
  async function initDefaultServer() {
    try {
      const resp = await fetch('/api/config', { cache: 'no-store' });
      if (resp.ok) {
        const cfg = await resp.json();
        if (cfg.defaultServer) {
          serverInput.value = cfg.defaultServer;
          return;
        }
      }
    } catch (e) { /* 非 Flask 环境（file:// 或纯静态托管）忽略 */ }
    serverInput.value = fallbackServer;
  }
  initDefaultServer();

  // ========== 全局对象 ==========
  const renderer = new Renderer(canvas, -1);
  const sound = new SoundManager();
  const music = new MusicManager();
  let net = null;
  let input = null;
  let started = false;

  // ========== 画布缩放（与桌面端等比缩放逻辑一致，支持放大与缩小） ==========
  const zoomControls = document.getElementById('zoomControls');
  const zoomOutBtn = document.getElementById('zoomOut');
  const zoomResetBtn = document.getElementById('zoomReset');
  const zoomInBtn = document.getElementById('zoomIn');
  const GAME_RATIO = 800 / 664;
  const ZOOM_MIN = 0.5;
  const ZOOM_MAX = 3;
  const ZOOM_STEP = 0.25;
  let zoom = 1; // 1 = 自动适配（完整显示）

  /** 按实际可视区计算 fit 尺寸并应用缩放因子。
   *  使用 window.innerWidth/innerHeight 而非 CSS 100vh，
   *  避免 iOS Safari 地址栏/工具栏导致画布超出可视区显示不全。 */
  function applyZoom() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let w = vw;
    let h = w / GAME_RATIO;
    if (h > vh) {
      h = vh;
      w = h * GAME_RATIO;
    }
    canvas.style.width = Math.max(1, Math.round(w * zoom)) + 'px';
    canvas.style.height = Math.max(1, Math.round(h * zoom)) + 'px';
    zoomResetBtn.textContent = Math.round(zoom * 100) + '%';
  }

  function setZoom(z) {
    zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
    applyZoom();
  }

  zoomOutBtn.addEventListener('click', () => setZoom(zoom - ZOOM_STEP));
  zoomInBtn.addEventListener('click', () => setZoom(zoom + ZOOM_STEP));
  zoomResetBtn.addEventListener('click', () => setZoom(1));
  window.addEventListener('resize', applyZoom);
  window.addEventListener('orientationchange', applyZoom);
  window.addEventListener('keydown', (e) => {
    if (e.key === '+' || e.key === '=') { setZoom(zoom + ZOOM_STEP); e.preventDefault(); }
    else if (e.key === '-' || e.key === '_') { setZoom(zoom - ZOOM_STEP); e.preventDefault(); }
    else if (e.key === '0') { setZoom(1); e.preventDefault(); }
  });
  applyZoom(); // 初始适配

  // ========== 连接状态 ==========
  function setStatus(text) {
    statusText.textContent = text;
  }

  function onStatus(status) {
    if (status === 'connecting') {
      setStatus('连接中...');
      joinBtn.disabled = true;
    } else if (status === 'connected') {
      setStatus('已连接，等待服务器确认...');
    } else if (status === 'reconnecting') {
      setStatus('连接断开，3 秒后自动重连...');
    }
  }

  // ========== 消息分发 ==========
  function onMessage(msg) {
    switch (msg.type) {
      case 'connect': {
        const pid = msg.content.player_id;
        if (pid >= 0) {
          renderer.selfPlayerId = pid;
          enterGame();
          // 服务器只在 mainMenu 状态接受新玩家，且 game_state_changed 仅在状态
          // 变化时推送（连接时不会收到）→ 此处主动初始化音乐状态为 mainMenu
          music.onGameStateChanged(0);
        } else {
          setStatus('服务器游戏已开始，无法加入');
          joinBtn.disabled = false;
        }
        break;
      }
      case 'screen_info':
        renderer.onScreenInfo(msg.content);
        break;
      case 'game_state_changed':
        renderer.onGameStateChanged(msg.content);
        music.onGameStateChanged(msg.content.state);
        break;
      case 'playsound':
        sound.play(msg.content.sound);
        break;
      case 'load_level':
        renderer.onLoadLevel(msg.content);
        break;
      case 'set_title':
        renderer.onSetTitle(msg.content);
        break;
      case 'particle_effect':
        renderer.onParticleEffect(msg.content);
        break;
      default:
        break;
    }
  }

  // ========== 进入游戏 ==========
  function enterGame() {
    if (started) return;
    started = true;
    if (input === null) {
      input = new InputManager(net, canvas, sound); // 连接成功后才启用输入
    }
    lobby.classList.add('hidden');
    gameDiv.classList.remove('hidden');
    zoomControls.classList.remove('hidden');
    applyZoom(); // 进入游戏时按当前可视区重算尺寸
    if (isTouchDevice()) {
      touchControls.classList.remove('hidden');
    }
    // 预加载图片完成后开始渲染循环
    renderer.loadImages().then(() => {
      requestAnimationFrame(loop);
    });
  }

  function loop(now) {
    renderer.draw(now);
    requestAnimationFrame(loop);
  }

  function isTouchDevice() {
    return ('ontouchstart' in window) || navigator.maxTouchPoints > 0;
  }

  // ========== 加入游戏 ==========
  function join() {
    const server = serverInput.value.trim() || fallbackServer;
    const name = nameInput.value.trim() || '{default}';
    net = new NetClient(server, onMessage, onStatus);
    net.connect(name);
  }

  joinBtn.addEventListener('click', join);
  serverInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') join(); });
  nameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') join(); });

  // 页面关闭时主动断开
  window.addEventListener('beforeunload', () => {
    if (net) net.disconnect();
  });
})();
