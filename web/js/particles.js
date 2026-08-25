/**
 * particles.js —— 完整复刻 particles.py 的粒子系统
 * 机制对应：Particle（插值/亮度抖动/多形状）、ParticleGroup（发射器/重力/阻尼/一次性）、
 * 全部效果类（EnemyExplosion 等 9 个）+ 拖尾类（MissileTrail/RocketTrail）。
 * 粒子更新频率与桌面一致：桌面在 60fps 渲染循环中每帧调用 ParticleGroup.update()，
 * Web 端同样每渲染帧（requestAnimationFrame）更新一次。
 * 旋转方向说明：pygame.transform.rotate 正角=视觉逆时针 → canvas 用 -angle；
 * triangle/diamond 在 particles.py 中用手动矩阵（视觉顺时针），此处照搬矩阵公式。
 */

/** 对应 particles.py _resolve：支持函数/二元组插值/二元组 RGB 插值 */
function resolve(val, t) {
  if (typeof val === 'function') return val(t);
  if (Array.isArray(val) && val.length === 2) {
    const a = val[0];
    const b = val[1];
    if (Array.isArray(a)) {
      return a.map((ai, i) => Math.round(ai + (b[i] - ai) * t));
    }
    return a + (b - a) * t;
  }
  return val;
}

/** 对应 particles.py _rand：二元数值组取随机均匀值 */
function rand(val) {
  if (Array.isArray(val) && val.length === 2 &&
      typeof val[0] === 'number' && typeof val[1] === 'number') {
    return val[0] + Math.random() * (val[1] - val[0]);
  }
  return val;
}

/** 对应 random.randint(lo, hi)，闭区间整数 */
function randInt(lo, hi) {
  return lo + Math.floor(Math.random() * (hi - lo + 1));
}

class Particle {
  constructor(kw = {}) {
    this.age = 0;
    this.alive = true;
    this.lifetime = Math.max(1, Math.round(rand(kw.lifetime ?? 60)));
    this.x = rand(kw.x ?? 0);
    this.y = rand(kw.y ?? 0);
    this.vx = rand(kw.vx ?? 0);
    this.vy = rand(kw.vy ?? 0);
    this.ax = rand(kw.ax ?? 0);
    this.ay = rand(kw.ay ?? 0);
    this._size = kw.size ?? 3;
    this._color = kw.color ?? [255, 255, 255];
    this._alpha = kw.alpha ?? 255;
    this._angle = 0;
    this._angularVel = kw.angular_vel ?? 0;
    this.shape = kw.shape ?? 'circle';
    this._surface = kw.surface ?? null;
    const jitter = kw.brightness_jitter ?? 0;
    this._brightness = jitter > 0 ? 1 + (Math.random() * 2 - 1) * jitter : 1;
    this.cachedSize = 0;
    this.cachedColor = [255, 255, 255];
    this.cachedAlpha = 255;
  }

  get t() {
    return this.lifetime > 0 ? Math.min(1, this.age / this.lifetime) : 1;
  }

  update() {
    if (!this.alive) return;
    this.age += 1;
    if (this.age >= this.lifetime) {
      this.alive = false;
      return;
    }
    const t = this.t;
    this.vx += this.ax;
    this.vy += this.ay;
    this.x += this.vx;
    this.y += this.vy;
    this._angle += resolve(this._angularVel, t);
    this.cachedSize = Math.max(0, resolve(this._size, t));
    const raw = resolve(this._color, t);
    if (this._brightness !== 1) {
      this.cachedColor = raw.map((c) => Math.max(0, Math.min(255, Math.round(c * this._brightness))));
    } else {
      this.cachedColor = raw;
    }
    this.cachedAlpha = Math.max(0, Math.min(255, Math.round(resolve(this._alpha, t))));
    this.cachedRgb = `rgb(${this.cachedColor[0]},${this.cachedColor[1]},${this.cachedColor[2]})`;
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} offsetX 组偏移
   * @param {number} offsetY 组偏移
   */
  draw(ctx, offsetX = 0, offsetY = 0) {
    if (!this.alive) return;
    const size = this.cachedSize;
    const alpha = this.cachedAlpha;
    if (alpha <= 0 || size <= 0) return;
    const px = this.x + offsetX;
    const py = this.y + offsetY;
    // 屏幕外裁剪（爆炸碎片大多很快飞出屏幕，跳过绘制大幅减少 canvas 调用）
    if (px < -32 || px > Renderer.LOGIC_W + 32 || py < -32 || py > Renderer.LOGIC_H + 32) return;
    const angle = this._angle;
    ctx.globalAlpha = alpha / 255;
    ctx.fillStyle = this.cachedRgb;
    if (this.shape === 'circle') {
      // 圆形旋转无视觉差异 → 免 rotate；小圆用 fillRect（免 beginPath/arc）
      if (size <= 3) {
        const d = Math.max(1, size * 2);
        ctx.fillRect(px - size, py - size, d, d);
      } else {
        ctx.beginPath();
        ctx.arc(px, py, Math.max(1, size), 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (this.shape === 'rect') {
      const s = Math.max(1, size);
      if (angle !== 0) {
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(-angle * Math.PI / 180); // 对应 pygame.rotate（视觉逆时针）
        ctx.fillRect(-s / 2, -s / 2, s, s);
        ctx.restore();
      } else {
        ctx.fillRect(px - s / 2, py - s / 2, s, s);
      }
    } else if (this.shape === 'triangle') {
      let pts = [[0, -size * 0.75], [-size / 2, size * 0.75], [size / 2, size * 0.75]];
      if (angle !== 0) {
        const rad = angle * Math.PI / 180;
        const c = Math.cos(rad);
        const s = Math.sin(rad);
        pts = pts.map(([q0, q1]) => [q0 * c - q1 * s, q0 * s + q1 * c]); // 照搬 particles.py 矩阵
      }
      ctx.beginPath();
      ctx.moveTo(px + pts[0][0], py + pts[0][1]);
      ctx.lineTo(px + pts[1][0], py + pts[1][1]);
      ctx.lineTo(px + pts[2][0], py + pts[2][1]);
      ctx.closePath();
      ctx.fill();
    } else if (this.shape === 'diamond') {
      let pts = [[0, -size], [-size, 0], [0, size], [size, 0]];
      if (angle !== 0) {
        const rad = angle * Math.PI / 180;
        const c = Math.cos(rad);
        const s = Math.sin(rad);
        pts = pts.map(([q0, q1]) => [q0 * c - q1 * s, q0 * s + q1 * c]);
      }
      ctx.beginPath();
      ctx.moveTo(px + pts[0][0], py + pts[0][1]);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(px + pts[i][0], py + pts[i][1]);
      ctx.closePath();
      ctx.fill();
    } else if (this.shape === 'surface' && this._surface) {
      const img = this._surface;
      if (angle !== 0) {
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(-angle * Math.PI / 180);
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        ctx.restore();
      } else {
        ctx.drawImage(img, px - img.width / 2, py - img.height / 2);
      }
    }
    ctx.globalAlpha = 1;
  }
}

class ParticleGroup {
  constructor(kw = {}) {
    this.particles = [];
    this.subgroups = [];
    this.x = kw.x ?? 0;
    this.y = kw.y ?? 0;
    this.spawnWidth = kw.spawn_width ?? 0;
    this.spawnHeight = kw.spawn_height ?? 0;
    this.emissionRate = kw.emission_rate ?? 0;
    this.maxParticles = kw.max_particles ?? 0;
    this._emitCounter = 0;
    this.particleKwargs = Object.assign({}, kw.particle_kwargs ?? {});
    if (kw.brightness_jitter !== undefined && !('brightness_jitter' in this.particleKwargs)) {
      this.particleKwargs.brightness_jitter = kw.brightness_jitter;
    }
    this.randomRanges = {};
    for (const key of ['vx', 'vy', 'ax', 'ay', 'lifetime']) {
      const rng = kw[key + '_range'];
      if (rng !== undefined && Array.isArray(rng) && rng.length === 2) {
        this.randomRanges[key] = [rng[0], rng[1]];
      }
    }
    this.gravity = kw.gravity ?? 0;
    this.wind = kw.wind ?? 0;
    this.damping = kw.damping ?? 1;
    this.active = kw.active ?? true;
    this.oneShot = kw.one_shot ?? false;
    this._hasEmitted = false;
  }

  emit(count = 1, overrides = {}) {
    for (let i = 0; i < count; i++) {
      const kw = Object.assign({}, this.particleKwargs);
      for (const key of Object.keys(this.randomRanges)) {
        const [lo, hi] = this.randomRanges[key];
        kw[key] = lo + Math.random() * (hi - lo);
      }
      Object.assign(kw, overrides); // overrides 最后生效（与 Python kw.update(overrides) 一致）
      if (this.spawnWidth > 0 || this.spawnHeight > 0) {
        kw.x = (kw.x ?? 0) + (Math.random() * 2 - 1) * this.spawnWidth / 2;
        kw.y = (kw.y ?? 0) + (Math.random() * 2 - 1) * this.spawnHeight / 2;
      }
      const p = new Particle(kw);
      p.ay += this.gravity;
      p.ax += this.wind;
      this.particles.push(p);
    }
    if (count > 0) this._hasEmitted = true;
  }

  update() {
    if (!this.active) return;
    if (this.emissionRate > 0) {
      if (!this.oneShot || !this._hasEmitted) {
        this._emitCounter += this.emissionRate;
        let emitCount = Math.floor(this._emitCounter);
        if (emitCount > 0) {
          this._emitCounter -= emitCount;
          if (this.maxParticles > 0) {
            emitCount = Math.min(emitCount, this.maxParticles - this.particles.length);
          }
          if (emitCount > 0) this.emit(emitCount);
        }
      }
    }
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.update();
      if (!p.alive) this.particles.splice(i, 1);
    }
    if (this.damping !== 1) {
      for (const p of this.particles) {
        p.vx *= this.damping;
        p.vy *= this.damping;
      }
    }
    for (const sg of this.subgroups) sg.update();
  }

  draw(ctx, offsetX = 0, offsetY = 0) {
    const ox = this.x + offsetX;
    const oy = this.y + offsetY;
    for (const p of this.particles) p.draw(ctx, ox, oy);
    for (const sg of this.subgroups) sg.draw(ctx, ox, oy);
  }

  get isDead() {
    return this.oneShot && this._hasEmitted && this.particles.length === 0;
  }

  get particleCount() {
    return this.particles.length;
  }
}

// ========== 一次性爆炸效果（对应 particles.py） ==========

class EnemyExplosion extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 10, spawn_height: 10,
      gravity: 0.05, damping: 0.97,
      particle_kwargs: {
        lifetime: [20, 40],
        size: [4, 0],
        color: [[255, 200, 50], [80, 20, 0]],
        alpha: [255, 0],
        shape: 'circle',
        brightness_jitter: 0.3,
      },
      vx_range: [-3, 3],
      vy_range: [-3, 3],
    });
    this.emit(randInt(15, 25));
  }
}

class MissileTrail extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: false,
      emission_rate: 0,
      max_particles: 30,
      gravity: 0.02,
      particle_kwargs: {
        lifetime: [15, 30],
        size: [3, 0.5],
        color: [[180, 180, 180], [80, 80, 80]],
        alpha: [200, 0],
        shape: 'circle',
        brightness_jitter: 0.3,
      },
    });
  }
}

class RocketTrail extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: false,
      emission_rate: 0,
      max_particles: 30,
      gravity: 0.02,
      particle_kwargs: {
        lifetime: [15, 30],
        size: [3, 0.5],
        color: [[255, 200, 50], [100, 30, 0]],
        alpha: [200, 0],
        shape: 'circle',
        brightness_jitter: 0.3,
      },
    });
  }
}

class MissileHit extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 8, spawn_height: 8,
      gravity: 0.08, damping: 0.96,
      particle_kwargs: {
        lifetime: [15, 25],
        size: [3, 0],
        color: [[255, 255, 255], [135, 216, 255]],
        alpha: [255, 0],
        shape: 'circle',
        brightness_jitter: 0.3,
      },
      vx_range: [-4, 4],
      vy_range: [-4, 4],
    });
    this.emit(randInt(10, 15));
  }
}

class RocketHit extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 8, spawn_height: 8,
      gravity: 0.08, damping: 0.96,
      particle_kwargs: {
        lifetime: [15, 25],
        size: [3, 0],
        color: [[255, 200, 80], [80, 20, 0]],
        alpha: [255, 0],
        shape: 'circle',
        brightness_jitter: 0.3,
      },
      vx_range: [-4, 4],
      vy_range: [-4, 4],
    });
    this.emit(randInt(20, 30));
  }
}

class PlayerExplosion extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 30, spawn_height: 30,
      gravity: 0.05, damping: 0.97,
      brightness_jitter: 0.3,
    });
    this.emit(
      randInt(30, 40),
      {
        lifetime: [30, 60],
        size: [8, 0],
        color: [[255, 255, 200], [255, 100, 0]],
        alpha: [255, 0],
        shape: 'circle',
        vx: [-6, 6], vy: [-6, 6],
      }
    );
    this.emit(
      randInt(15, 25),
      {
        lifetime: [40, 80],
        size: [5, 1],
        color: [[200, 200, 200], [50, 50, 50]],
        alpha: [150, 0],
        shape: 'circle',
        vx: [-4, 4], vy: [-4, 4],
      }
    );
    this.emit(
      randInt(10, 15),
      {
        lifetime: [10, 25],
        size: [2, 0],
        color: [[255, 255, 255], [255, 200, 0]],
        alpha: [255, 0],
        shape: 'rect',
        vx: [-10, 10], vy: [-10, 10],
      }
    );
  }
}

class NukeExplosion extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 30, spawn_height: 30,
      brightness_jitter: 0.3,
    });
    this.emit(1, { lifetime: 15, size: [350, 0], color: [255, 255, 255], alpha: [200, 0], shape: 'circle', vx: 0, vy: 0 });
    this.emit(
      120,
      {
        lifetime: [30, 90],
        size: [10, 0],
        color: [[255, 255, 200], [200, 50, 0]],
        alpha: [255, 0],
        shape: 'circle',
        vx: [-8, 8], vy: [-8, 8],
      }
    );
    this.emit(
      80,
      {
        lifetime: [30, 90],
        size: [5, 1],
        color: [[255, 200, 100], [100, 30, 0]],
        alpha: [200, 0],
        shape: 'circle',
        vx: [-12, 12], vy: [-12, 12],
      }
    );
    this.emit(
      100,
      {
        lifetime: [60, 120],
        size: [15, 3],
        color: [[150, 150, 150], [30, 30, 30]],
        alpha: [180, 0],
        shape: 'circle',
        vx: [-3, 3], vy: [-4, -2],
      }
    );
    this.emit(
      60,
      {
        lifetime: [50, 100],
        size: [4, 1],
        color: [[200, 200, 150], [80, 80, 50]],
        alpha: [255, 0],
        shape: 'rect',
        vx: [-15, 15], vy: [-15, 15],
      }
    );
    this.emit(
      40,
      {
        lifetime: [80, 150],
        size: [2, 0],
        color: [[180, 180, 180], [100, 100, 100]],
        alpha: [100, 0],
        shape: 'circle',
        vx: [-3, 3], vy: [0.5, 2],
      }
    );
  }
}

class BulletHit extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 4, spawn_height: 4,
      brightness_jitter: 0.3,
      particle_kwargs: {
        lifetime: [8, 15],
        size: [3, 0],
        color: [[255, 200, 50], [180, 120, 20]],
        alpha: [255, 0],
        shape: 'circle',
      },
      vx_range: [-2, 2],
      vy_range: [-2, 2],
    });
    this.emit(randInt(4, 7));
  }
}

class LazerHit extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 4, spawn_height: 4,
      brightness_jitter: 0.3,
      particle_kwargs: {
        lifetime: [8, 15],
        size: [3, 0],
        color: [[100, 200, 255], [30, 100, 200]],
        alpha: [255, 0],
        shape: 'circle',
      },
      vx_range: [-2, 2],
      vy_range: [-2, 2],
    });
    this.emit(randInt(4, 7));
  }
}

class AutocannonHit extends ParticleGroup {
  constructor(x, y) {
    super({
      x, y,
      one_shot: true,
      spawn_width: 4, spawn_height: 4,
      brightness_jitter: 0.3,
      particle_kwargs: {
        lifetime: [8, 15],
        size: [5, 0],
        color: [[255, 150, 150], [200, 80, 80]],
        alpha: [255, 0],
        shape: 'circle',
      },
      vx_range: [-3, 3],
      vy_range: [-3, 3],
    });
    this.emit(randInt(4, 7));
  }
}
