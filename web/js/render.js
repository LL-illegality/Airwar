/**
 * Renderer —— Canvas 渲染
 * 逻辑分辨率固定 800x664（与桌面端一致），世界坐标与画布坐标严格对应；
 * 画布通过 CSS 等比缩放适配窗口（黑边由 CSS 保证）。
 * 实体渲染采用双帧插值（与桌面 main.py 的 prevEntities/currEntities 一致）；
 * 粒子渲染对齐桌面 main.py ImageLoader：每渲染帧更新粒子组与拖尾，
 * 绘制顺序为 背景 → 拖尾 → 粒子组 → 标题 → 关卡名 → 实体 → 暂停遮罩。
 */
class Renderer {
  static LOGIC_W = 800;
  static LOGIC_H = 664;

  /** 粒子总数软上限（超出后从最旧爆炸组截断，防止大规模战斗时帧率骤降） */
  static MAX_PARTICLES = 900;

  /** 与 const.py Images 枚举值一致 */
  static IMAGE_NAMES = [
    'player1', 'player2', 'bullet1', 'bullet_enemy',
    'lazer_level1', 'lazer_level2', 'lazer_level3', 'lazer_level4', 'lazer_level5',
    'lazer_level6', 'lazer_level7', 'lazer_level8', 'lazer_level9', 'lazer_level10',
    'autocannon_level12', 'autocannon_level34', 'autocannon_level56',
    'autocannon_level7', 'autocannon_level8', 'autocannon_level9', 'autocannon_level10',
    'missile', 'unit1', 'big1', 'big2', 'rocket', 'rocket_enemy',
    'energyball', 'energyball_enhanced', 'magabomb',
    'en', 'enemy2', 'enemy3', 'enemy4', 'enemy5', 'ready', 'enemy',
    'rship', 'rship2', 'rship3', 'rship4', 'ca', 'boss1', 'boss2',
    'item_shotgun', 'item_missile', 'item_lazer', 'item_autocannon',
    'item_super', 'item_rocket', 'item_maga', 'item_medic',
  ];

  /**
   * @param {HTMLCanvasElement} canvas
   * @param {number} selfPlayerId 本机玩家 id（-1 表示未知）
   */
  constructor(canvas, selfPlayerId) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.selfPlayerId = selfPlayerId;
    this.images = {};            // name -> HTMLImageElement
    // 粒子（对应桌面 ImageLoader.particle_groups / projectile_trails）
    this.particleGroups = [];    // 一次性爆炸效果 + 退场拖尾
    this.projectileTrails = new Map(); // entityId -> ParticleGroup（导弹/火箭拖尾）
    this.prevEntities = new Map(); // id -> entity
    this.currEntities = new Map(); // id -> entity
    this.lastUpdateTime = 0;
    this.titleInfo = [];         // {text, duration, delay}
    this.levelInfo = '';
    this.isPaused = false;
    this.pausePlayerName = '';
    this.gameState = 0;          // GameState: 0 mainMenu ...
    // 程序化背景（复刻 background.py：天空/云/河流/山脉）
    this.bg = new Background(Renderer.LOGIC_W, Renderer.LOGIC_H);
  }

  /** 预加载全部游戏图片（相对项目根 images/） */
  async loadImages(base = '../images/') {
    const tasks = Renderer.IMAGE_NAMES.map((name) => new Promise((resolve) => {
      const img = new Image();
      img.onload = () => { this.images[name] = img; resolve(); };
      img.onerror = () => resolve(); // 缺失图片忽略
      img.src = base + name + '.png';
    }));
    await Promise.all(tasks);
  }

  // ========== 服务器消息处理 ==========

  onScreenInfo(content) {
    const objList = content.objects || [];
    this.prevEntities = this.currEntities;
    this.currEntities = new Map();
    for (const d of objList) this.currEntities.set(d.id, d);
    this.lastUpdateTime = performance.now();
    if (typeof content.isPaused === 'boolean') {
      this.isPaused = content.isPaused;
      this.pausePlayerName = content.pausePlayerName || '';
    }
  }

  onParticleEffect(content) {
    const pg = this._createParticleEffect(content.effect || '', content.x || 0, content.y || 0);
    if (pg !== null) this.particleGroups.push(pg);
  }

  /** 对应桌面 ImageLoader._create_particle_effect */
  _createParticleEffect(effect, x, y) {
    switch (effect) {
      case 'enemy_explosion': return new EnemyExplosion(x, y);
      case 'player_explosion': return new PlayerExplosion(x, y);
      case 'missile_hit': return new MissileHit(x, y);
      case 'rocket_hit': return new RocketHit(x, y);
      case 'nuke_explosion': return new NukeExplosion(x, y);
      case 'bullet_hit': return new BulletHit(x, y);
      case 'lazer_hit': return new LazerHit(x, y);
      case 'autocannon_hit': return new AutocannonHit(x, y);
      default: return null;
    }
  }

  onSetTitle(content) {
    this.titleInfo = [{ text: String(content.title || ''), duration: content.duration || 0, delay: content.duration || 0 }];
  }

  onLoadLevel(content) {
    this.levelInfo = String(content.level || '');
  }

  onGameStateChanged(content) {
    this.gameState = content.state || 0;
  }

  // ========== 粒子更新（对应桌面 ImageLoader.update_particles） ==========

  /** 移植 main.py ImageLoader._update_trails：导弹/火箭拖尾跟随实体并发射 */
  _updateTrails() {
    const trailIds = new Set();
    for (const data of this.currEntities.values()) {
      const img = data.image;
      if (img !== 'missile' && img !== 'rocket' && img !== 'rocket_enemy') continue;
      const eid = data.id;
      trailIds.add(eid);
      let trail = this.projectileTrails.get(eid);
      if (!trail) {
        trail = img === 'missile' ? new MissileTrail(data.x, data.y) : new RocketTrail(data.x, data.y);
        this.projectileTrails.set(eid, trail);
      }
      const rad = data.rotation * Math.PI / 180;
      trail.x = data.x - 8 * Math.sin(rad);
      trail.y = data.y + 8 * Math.cos(rad);
      if (trail.particles.length < trail.maxParticles) {
        const bx = -Math.sin(rad);
        const by = Math.cos(rad);
        let vx;
        let vy;
        if (img === 'missile') {
          vx = bx * 2 + (Math.random() - 0.5);
          vy = by * 2 + (Math.random() - 0.5);
        } else {
          vx = bx * 3 + (Math.random() * 2 - 1);
          vy = by * 3 + (Math.random() * 2 - 1);
        }
        trail.emit(1, { vx, vy });
      }
    }
    // 实体消失的拖尾转为普通粒子组，自然消散
    for (const eid of Array.from(this.projectileTrails.keys())) {
      if (!trailIds.has(eid)) {
        const trail = this.projectileTrails.get(eid);
        this.projectileTrails.delete(eid);
        trail.emissionRate = 0;
        this.particleGroups.push(trail);
      }
    }
  }

  /** 对应桌面 ImageLoader._update_particle_groups */
  _updateParticleGroups() {
    for (let i = this.particleGroups.length - 1; i >= 0; i--) {
      const pg = this.particleGroups[i];
      pg.update();
      if (pg.particleCount === 0) this.particleGroups.splice(i, 1);
    }
    for (const trail of this.projectileTrails.values()) {
      trail.update();
    }
    // 粒子总数软上限：超出时从最旧组截断，防止场上单位多时粒子拖垮帧率
    let total = 0;
    for (const pg of this.particleGroups) total += pg.particleCount;
    for (const trail of this.projectileTrails.values()) total += trail.particleCount;
    if (total > Renderer.MAX_PARTICLES) {
      let excess = total - Renderer.MAX_PARTICLES;
      for (let i = 0; i < this.particleGroups.length && excess > 0; i++) {
        const pg = this.particleGroups[i];
        const cut = Math.min(excess, pg.particles.length);
        if (cut > 0) {
          pg.particles.splice(pg.particles.length - cut, cut);
          excess -= cut;
        }
      }
    }
  }

  // ========== 渲染 ==========

  /** @param {number} now performance.now() */
  draw(now) {
    const ctx = this.ctx;
    // 更新与绘制顺序对齐桌面 main.py：更新粒子/背景 → 背景 → 拖尾 → 粒子组 → 实体 → 遮罩
    this._updateTrails();
    this._updateParticleGroups();
    this.bg.update();
    this.bg.draw(ctx);
    for (const trail of this.projectileTrails.values()) trail.draw(ctx);
    for (const pg of this.particleGroups) pg.draw(ctx);
    this._drawEntities(ctx, now);
    this._drawTitle(ctx);
    this._drawLevelInfo(ctx);
    this._drawPause(ctx);
  }

  _drawEntities(ctx, now) {
    // 插值系数：gametick=30，与桌面端一致
    const t = Math.min(1, Math.max(0, (now - this.lastUpdateTime) * 30 / 1000));
    // 第一遍：图片绘制（setTransform 替代 save/translate/rotate/restore，减少状态栈开销）
    for (const [id, data] of this.currEntities) {
      const prev = this.prevEntities.get(id) || data;
      const x = prev.x + (data.x - prev.x) * t;
      const y = prev.y + (data.y - prev.y) * t;
      // 屏幕外裁剪（含最大图片尺寸边距）：场上单位多时大幅减少 drawImage
      if (x < -80 || x > Renderer.LOGIC_W + 80 || y < -80 || y > Renderer.LOGIC_H + 80) continue;
      const img = this.images[data.image];
      if (!img) continue;
      const rot = prev.rotation + (data.rotation - prev.rotation) * t;
      const rad = rot * Math.PI / 180;
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);
      // 等价 ctx.translate(x,y) + ctx.rotate(rad)，一次调用完成
      ctx.setTransform(cos, sin, -sin, cos, x, y);
      if (typeof data.alpha === 'number') {
        ctx.globalAlpha = data.alpha / 255;
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        ctx.globalAlpha = 1;
      } else {
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
      }
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    // 第二遍：UI 叠加（准备勾/名字/状态栏，仅玩家与主菜单场景，开销小）
    for (const [id, data] of this.currEntities) {
      const prev = this.prevEntities.get(id) || data;
      const x = prev.x + (data.x - prev.x) * t;
      const y = prev.y + (data.y - prev.y) * t;
      // 主菜单准备勾
      if (data.isReady && this.gameState === 0) {
        const tick = this.images['ready'];
        if (tick) ctx.drawImage(tick, x - tick.width / 2, y - 48 - tick.height / 2);
      }
      // 玩家名
      if (data.name !== undefined) {
        ctx.fillStyle = '#131313';
        ctx.font = '14px Consolas';
        ctx.textAlign = 'center';
        ctx.fillText(data.name, x, y + 34);
      }
      // 自己的状态栏（底部 64px）
      if (data.player_id !== undefined && data.player_id === this.selfPlayerId) {
        this._drawStateBar(ctx, data);
      }
    }
  }

  _drawStateBar(ctx, data) {
    const barY = Renderer.LOGIC_H - 64;
    ctx.fillStyle = '#c0c0c0';
    ctx.fillRect(0, barY, Renderer.LOGIC_W, 64);
    ctx.fillStyle = '#131313';
    ctx.font = '20px Consolas';
    ctx.textAlign = 'left';
    ctx.fillText('Player ' + data.name, 8, barY + 22);
    ctx.fillText('HP:', 8, barY + 46);
    ctx.strokeStyle = '#131313';
    ctx.lineWidth = 1;
    ctx.strokeRect(48, barY + 34, 202, 18);
    const hp = Math.max(0, Math.min(100, data.health || 0));
    ctx.fillStyle = `rgb(${Math.round(255 * (1 - hp / 100))},${Math.round(255 * (hp / 100))},0)`;
    ctx.fillRect(49, barY + 35, hp * 2, 16);
    const bomb = this.images['item_maga'];
    if (bomb) {
      const n = Math.max(0, data.magabombQuantity || 0);
      for (let i = 0; i < n; i++) {
        ctx.drawImage(bomb, Renderer.LOGIC_W - 44 - i * 32, barY + 24, 24, 24);
      }
    }
  }

  _drawTitle(ctx) {
    const list = this.titleInfo;
    for (let i = list.length - 1; i >= 0; i--) {
      const t = list[i];
      ctx.fillStyle = '#131313';
      ctx.font = '30px "Microsoft YaHei", sans-serif';
      ctx.textAlign = 'center';
      if (t.delay <= 30) {
        ctx.globalAlpha = Math.max(0, t.delay / 30);
      }
      ctx.fillText(t.text, Renderer.LOGIC_W / 2, Renderer.LOGIC_H / 4);
      ctx.globalAlpha = 1;
      t.delay -= 1;
      if (t.delay <= 0) list.splice(i, 1);
    }
  }

  _drawLevelInfo(ctx) {
    if (this.titleInfo.length > 0 || !this.levelInfo) return;
    ctx.fillStyle = '#131313';
    ctx.font = '20px Consolas';
    ctx.textAlign = 'center';
    ctx.fillText(this.levelInfo, Renderer.LOGIC_W / 2, 24);
  }

  _drawPause(ctx) {
    if (!this.isPaused) return;
    ctx.fillStyle = 'rgba(100,100,100,0.62)';
    ctx.fillRect(0, 0, Renderer.LOGIC_W, Renderer.LOGIC_H);
    ctx.fillStyle = '#fff';
    ctx.font = '30px "Microsoft YaHei", sans-serif';
    ctx.textAlign = 'center';
    const text = this.pausePlayerName ? this.pausePlayerName + '暂停了游戏' : '游戏暂停';
    ctx.fillText(text, Renderer.LOGIC_W / 2, Renderer.LOGIC_H / 3);
  }
}
