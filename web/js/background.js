/**
 * background.js —— 完整复刻 background.py 的程序化背景（天空/云/河流/山脉）
 * 常量与逻辑一一对应（const.py Background Configuration 段）。
 * 更新频率：与桌面 main.py 一致，每渲染帧 update() + draw()。
 * 绘制顺序：天空 → 山脉 → 河流 → 云。
 */

// ===== 常量（对应 const.py） =====
const BG_SCROLL_SPEED = 0.3;
const BG_REMOVE_MARGIN = 80;
const BG_VISIBLE_MARGIN = 30;

const SKY_TOP_RGB = [90, 160, 215];
const SKY_BOTTOM_RGB = [35, 90, 150];

const CLOUD_GRAY_MIN = 192;
const CLOUD_GRAY_MAX = 255;
const CLOUD_ALPHA_MIN = 20;
const CLOUD_ALPHA_MAX = 120;
const CLOUD_SPAWN_X_OFFSET = 50;
const CLOUD_Y_ABOVE_MIN = 10;
const CLOUD_Y_ABOVE_MAX = 60;
const CLOUD_BLOCK_COUNT_MIN = 3;
const CLOUD_BLOCK_COUNT_MAX = 8;
const CLOUD_BLOCK_W_MIN = 10;
const CLOUD_BLOCK_W_MAX = 35;
const CLOUD_BLOCK_H_MIN = 6;
const CLOUD_BLOCK_H_MAX = 18;
const CLOUD_BLOCK_X_MIN = -25;
const CLOUD_BLOCK_X_MAX = 25;
const CLOUD_BLOCK_Y_MIN = -20;
const CLOUD_BLOCK_Y_MAX = 20;
const CLOUD_SPEED_MIN = 0.3;
const CLOUD_SPEED_MAX = 1.2;
const CLOUD_SPAWN_CHANCE = 0.025;
const CLOUD_INITIAL_COUNT = 10;

const RIVER_COUNT_MIN = 1;
const RIVER_COUNT_MAX = 3;
const RIVER_NUM_POINTS = 10000;
const RIVER_START_Y = -200000.0;
const RIVER_X_STEP_MIN = -50;
const RIVER_X_STEP_MAX = 50;
const RIVER_Y_STEP_MIN = 15;
const RIVER_Y_STEP_MAX = 30;
const RIVER_GRAY_MIN = 192;
const RIVER_GRAY_MAX = 200;
const RIVER_WIDTH_MIN = 2;
const RIVER_WIDTH_MAX = 10;
const RIVER_ALPHA_MIN = 20;
const RIVER_ALPHA_MAX = 80;
const RIVER_DRAW_STEP = 10;
const RIVER_X_OFFSET = 30;
const RIVER_X_CLAMP_MIN = 10;
const RIVER_LIFE_MIN = 1800;
const RIVER_LIFE_MAX = 5400;
const RIVER_FADE_DURATION = 600;
const RIVER_SPAWN_CHANCE = 0.0008;
const RIVER_SPAWN_Y_ABOVE = 200;
const RIVER_FADE_IN_DURATION = 600;

const MOUNTAIN_X_MARGIN = 20;
const MOUNTAIN_Y_ABOVE_MIN = 20;
const MOUNTAIN_Y_ABOVE_MAX = 60;
const MOUNTAIN_COLLISION_DIST = 25;
const MOUNTAIN_COLLISION_IDX_RANGE = 2;
const MOUNTAIN_SIZE_W_MIN = 30;
const MOUNTAIN_SIZE_W_MAX = 80;
const MOUNTAIN_SIZE_H_MIN = 20;
const MOUNTAIN_SIZE_H_MAX = 50;
const MOUNTAIN_SCALE_MIN = 0.5;
const MOUNTAIN_SCALE_MAX = 2.5;
const MOUNTAIN_BIG_CHANCE = 0.15;
const MOUNTAIN_BIG_SCALE_W_MIN = 1.8;
const MOUNTAIN_BIG_SCALE_W_MAX = 3.0;
const MOUNTAIN_BIG_SCALE_H_MIN = 1.5;
const MOUNTAIN_BIG_SCALE_H_MAX = 2.5;
const MOUNTAIN_COLOR_MIN = 30;
const MOUNTAIN_COLOR_MAX = 60;
const MOUNTAIN_MAX_ALPHA = 20;
const MOUNTAIN_ALPHA_OFFSET_MIN = 1.0;
const MOUNTAIN_ALPHA_OFFSET_MAX = 3.0;
const MOUNTAIN_SPAWN_CHANCE = 0.008;
const MOUNTAIN_INITIAL_COUNT = 12;

function bgRandInt(lo, hi) {
  return lo + Math.floor(Math.random() * (hi - lo + 1));
}

/** 对应 Python bisect.bisect_left：返回插入位置（第一个 >= val 的下标） */
function bisectLeft(arr, val) {
  let lo = 0;
  let hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (arr[mid] < val) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

class Background {
  /**
   * @param {number} width 逻辑宽度
   * @param {number} height 逻辑高度
   */
  constructor(width, height) {
    this.width = width;
    this.height = height;
    this.scrollSpeed = BG_SCROLL_SPEED;
    this.skyCanvas = this._createSky();
    this.clouds = [];
    this.rivers = [];
    this.mountains = [];
    this._generateRivers();
    for (let i = 0; i < CLOUD_INITIAL_COUNT; i++) {
      this._spawnCloud();
      const last = this.clouds[this.clouds.length - 1];
      if (last) {
        last.x = Math.random() * (width + CLOUD_SPAWN_X_OFFSET * 2) - CLOUD_SPAWN_X_OFFSET;
        last.y = Math.random() * height;
      }
    }
    for (let i = 0; i < MOUNTAIN_INITIAL_COUNT; i++) {
      this._spawnMountain();
      const last = this.mountains[this.mountains.length - 1];
      if (last) last.y = Math.random() * height;
    }
  }

  /** 天空渐变（对应 _create_sky 逐行插值，canvas 用线性渐变等效） */
  _createSky() {
    const canvas = document.createElement('canvas');
    canvas.width = this.width;
    canvas.height = this.height;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, this.height);
    grad.addColorStop(0, `rgb(${SKY_TOP_RGB[0]},${SKY_TOP_RGB[1]},${SKY_TOP_RGB[2]})`);
    grad.addColorStop(1, `rgb(${SKY_BOTTOM_RGB[0]},${SKY_BOTTOM_RGB[1]},${SKY_BOTTOM_RGB[2]})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, this.width, this.height);
    return canvas;
  }

  /** 云：矩形块拼成离屏表面（对应 _spawn_cloud） */
  _spawnCloud() {
    const g = bgRandInt(CLOUD_GRAY_MIN, CLOUD_GRAY_MAX);
    const alpha = bgRandInt(CLOUD_ALPHA_MIN, CLOUD_ALPHA_MAX);
    const color = `rgba(${g},${g},${g},${alpha / 255})`;
    const blocks = [];
    const cx = bgRandInt(-CLOUD_SPAWN_X_OFFSET, this.width + CLOUD_SPAWN_X_OFFSET);
    const cy = -bgRandInt(CLOUD_Y_ABOVE_MIN, CLOUD_Y_ABOVE_MAX);
    const n = bgRandInt(CLOUD_BLOCK_COUNT_MIN, CLOUD_BLOCK_COUNT_MAX);
    let minBx = 99999;
    let minBy = 99999;
    let maxBx = -99999;
    let maxBy = -99999;
    for (let i = 0; i < n; i++) {
      const bw = bgRandInt(CLOUD_BLOCK_W_MIN, CLOUD_BLOCK_W_MAX);
      const bh = bgRandInt(CLOUD_BLOCK_H_MIN, CLOUD_BLOCK_H_MAX);
      const bx = bgRandInt(CLOUD_BLOCK_X_MIN, CLOUD_BLOCK_X_MAX);
      const by = bgRandInt(CLOUD_BLOCK_Y_MIN, CLOUD_BLOCK_Y_MAX);
      blocks.push([bx, by, bw, bh]);
      minBx = Math.min(minBx, bx);
      minBy = Math.min(minBy, by);
      maxBx = Math.max(maxBx, bx + bw);
      maxBy = Math.max(maxBy, by + bh);
    }
    const w = maxBx - minBx;
    const h = maxBy - minBy;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    for (const [bx, by, bw, bh] of blocks) {
      ctx.fillRect(bx - minBx, by - minBy, bw, bh);
    }
    const speed = CLOUD_SPEED_MIN + Math.random() * (CLOUD_SPEED_MAX - CLOUD_SPEED_MIN);
    this.clouds.push({ x: cx + minBx, y: cy + minBy, speed, canvas });
  }

  /** 生成一条河（对应 _generate_river） */
  _generateRiver(xPos = null, startOffset = 0.0) {
    let cx = xPos !== null ? xPos : RIVER_X_CLAMP_MIN + Math.random() * (this.width - RIVER_X_CLAMP_MIN * 2);
    let cy = RIVER_START_Y;
    const ptsX = [];
    const ptsY = [];
    for (let i = 0; i < RIVER_NUM_POINTS; i++) {
      ptsX.push(cx);
      ptsY.push(cy);
      cx += RIVER_X_STEP_MIN + Math.random() * (RIVER_X_STEP_MAX - RIVER_X_STEP_MIN);
      cx = Math.max(RIVER_X_CLAMP_MIN, Math.min(this.width - RIVER_X_CLAMP_MIN, cx));
      cy += RIVER_Y_STEP_MIN + Math.random() * (RIVER_Y_STEP_MAX - RIVER_Y_STEP_MIN);
    }
    const gray = bgRandInt(RIVER_GRAY_MIN, RIVER_GRAY_MAX);
    const life = bgRandInt(RIVER_LIFE_MIN, RIVER_LIFE_MAX);
    return {
      pts_x: ptsX,
      pts_y: ptsY,
      offset: startOffset,
      color: [gray, gray, gray],
      width: RIVER_WIDTH_MIN + Math.random() * (RIVER_WIDTH_MAX - RIVER_WIDTH_MIN),
      alpha: bgRandInt(RIVER_ALPHA_MIN, RIVER_ALPHA_MAX),
      life,
      max_life: life,
    };
  }

  _generateRivers() {
    const count = bgRandInt(RIVER_COUNT_MIN, RIVER_COUNT_MAX);
    const spacing = this.width / (count + 1);
    for (let i = 0; i < count; i++) {
      const x = spacing * (i + 1) + Math.random() * (RIVER_X_OFFSET * 2) - RIVER_X_OFFSET;
      this.rivers.push(this._generateRiver(x));
    }
  }

  _spawnNewRiver() {
    const x = RIVER_X_CLAMP_MIN + Math.random() * (this.width - RIVER_X_CLAMP_MIN * 2);
    // 注意：background.py 的 _spawn_new_river 计算了 offset 但未传入 _generate_river
    // （实际生效 start_offset=0.0），此处保持与桌面行为一致，不传 startOffset
    this.rivers.push(this._generateRiver(x));
  }

  /** 山脉：离屏表面逐像素 alpha 三角（对应 _spawn_mountain） */
  _spawnMountain() {
    const x = bgRandInt(MOUNTAIN_X_MARGIN, this.width - MOUNTAIN_X_MARGIN);
    const my = -bgRandInt(MOUNTAIN_Y_ABOVE_MIN, MOUNTAIN_Y_ABOVE_MAX);
    for (const river of this.rivers) {
      const ry = my - river.offset;
      let idx = bisectLeft(river.pts_y, ry) - 1;
      idx = Math.max(0, idx);
      for (let i = Math.max(0, idx - MOUNTAIN_COLLISION_IDX_RANGE);
           i < Math.min(river.pts_x.length, idx + MOUNTAIN_COLLISION_IDX_RANGE + 1); i++) {
        if (Math.abs(river.pts_x[i] - x) < MOUNTAIN_COLLISION_DIST) return;
      }
    }
    const scale = MOUNTAIN_SCALE_MIN + Math.random() * (MOUNTAIN_SCALE_MAX - MOUNTAIN_SCALE_MIN);
    let w = Math.round(bgRandInt(MOUNTAIN_SIZE_W_MIN, MOUNTAIN_SIZE_W_MAX) * scale);
    let h = Math.round(bgRandInt(MOUNTAIN_SIZE_H_MIN, MOUNTAIN_SIZE_H_MAX) * scale);
    if (Math.random() < MOUNTAIN_BIG_CHANCE) {
      w = Math.round(w * (MOUNTAIN_BIG_SCALE_W_MIN + Math.random() * (MOUNTAIN_BIG_SCALE_W_MAX - MOUNTAIN_BIG_SCALE_W_MIN)));
      h = Math.round(h * (MOUNTAIN_BIG_SCALE_H_MIN + Math.random() * (MOUNTAIN_BIG_SCALE_H_MAX - MOUNTAIN_BIG_SCALE_H_MIN)));
    }
    const c = bgRandInt(MOUNTAIN_COLOR_MIN, MOUNTAIN_COLOR_MAX);
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(w, h);
    const half = w / 2;
    const aoff = MOUNTAIN_ALPHA_OFFSET_MIN + Math.random() * (MOUNTAIN_ALPHA_OFFSET_MAX - MOUNTAIN_ALPHA_OFFSET_MIN);
    for (let px = 0; px < w; px++) {
      const dist = Math.abs(px - half) / half;
      const hh = Math.round((1 - dist) * h);
      if (hh > 0) {
        const a = Math.round((px / w) * MOUNTAIN_MAX_ALPHA * aoff);
        for (let py = h - hh; py < h; py++) {
          const i = (py * w + px) * 4;
          imgData.data[i] = c;
          imgData.data[i + 1] = c;
          imgData.data[i + 2] = c;
          imgData.data[i + 3] = a;
        }
      }
    }
    ctx.putImageData(imgData, 0, 0);
    this.mountains.push([x, -bgRandInt(MOUNTAIN_Y_ABOVE_MIN, MOUNTAIN_Y_ABOVE_MAX), canvas]);
  }

  /** 河流屏幕采样点（对应 _river_pts），offset 变化 <1px 时复用缓存 */
  _riverPts(river) {
    if (river.cachedPts && Math.abs(river.offset - river.cachedOffset) < 1.0) {
      return river.cachedPts;
    }
    const pts = [];
    const margin = BG_VISIBLE_MARGIN;
    const step = RIVER_DRAW_STEP;
    for (let sy = -margin; sy <= this.height + margin; sy += step) {
      const ry = sy - river.offset;
      let idx = bisectLeft(river.pts_y, ry);
      idx = Math.max(1, Math.min(idx, river.pts_x.length - 1));
      const y0 = river.pts_y[idx - 1];
      const y1 = river.pts_y[idx];
      let x;
      if (y1 > y0) {
        const f = (ry - y0) / (y1 - y0);
        x = river.pts_x[idx - 1] + (river.pts_x[idx] - river.pts_x[idx - 1]) * f;
      } else {
        x = river.pts_x[idx - 1];
      }
      pts.push([Math.round(x), Math.round(sy)]);
    }
    river.cachedPts = pts;
    river.cachedOffset = river.offset;
    return pts;
  }

  update() {
    const margin = BG_REMOVE_MARGIN;
    for (let i = this.clouds.length - 1; i >= 0; i--) {
      const cloud = this.clouds[i];
      cloud.y += cloud.speed;
      if (cloud.y > this.height + margin) this.clouds.splice(i, 1);
    }
    if (Math.random() < CLOUD_SPAWN_CHANCE) this._spawnCloud();
    for (let i = this.rivers.length - 1; i >= 0; i--) {
      const river = this.rivers[i];
      river.offset += this.scrollSpeed;
      river.life -= 1;
      if (river.life <= 0 && this.rivers.length > RIVER_COUNT_MIN) this.rivers.splice(i, 1);
    }
    if (this.rivers.length < RIVER_COUNT_MAX && Math.random() < RIVER_SPAWN_CHANCE) {
      this._spawnNewRiver();
    }
    for (let i = this.mountains.length - 1; i >= 0; i--) {
      this.mountains[i][1] += this.scrollSpeed;
      if (this.mountains[i][1] > this.height + margin) this.mountains.splice(i, 1);
    }
    if (Math.random() < MOUNTAIN_SPAWN_CHANCE) this._spawnMountain();
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   */
  draw(ctx) {
    ctx.drawImage(this.skyCanvas, 0, 0);
    for (const [mx, my, surf] of this.mountains) {
      ctx.drawImage(surf, mx - surf.width / 2, Math.floor(my));
    }
    for (const river of this.rivers) {
      const pts = this._riverPts(river);
      if (pts.length > 1) {
        let baseAlpha = river.alpha;
        const elapsed = river.max_life - river.life;
        if (elapsed < RIVER_FADE_IN_DURATION) {
          baseAlpha = Math.round(baseAlpha * elapsed / RIVER_FADE_IN_DURATION);
        }
        if (river.life < RIVER_FADE_DURATION) {
          baseAlpha = Math.round(baseAlpha * river.life / RIVER_FADE_DURATION);
        }
        baseAlpha = Math.max(0, Math.min(255, baseAlpha));
        ctx.save();
        ctx.strokeStyle = `rgba(${river.color[0]},${river.color[1]},${river.color[2]},${baseAlpha / 255})`;
        ctx.lineWidth = Math.max(1, Math.round(river.width));
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
        ctx.stroke();
        ctx.restore();
      }
    }
    for (const cloud of this.clouds) {
      ctx.drawImage(cloud.canvas, Math.round(cloud.x), Math.round(cloud.y));
    }
  }
}