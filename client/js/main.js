// ── State ──────────────────────────────────────────────────────────────────
const canvas  = document.getElementById('gameCanvas');
const ctx     = canvas.getContext('2d');

let sessionId  = null;
let numPlayers = 1;
let gameState  = null;
let running    = false;
let won        = false;

// Tracks which keys are currently held
const keys = {};

// ── Keybindings ────────────────────────────────────────────────────────────
// P1: Arrow keys       P2: WASD
const BINDINGS = {
  p1: { left: 'ArrowLeft', right: 'ArrowRight', jump: 'ArrowUp' },
  p2: { left: 'KeyA',      right: 'KeyD',       jump: 'KeyW'    }
};

document.addEventListener('keydown', e => { keys[e.code] = true;  });
document.addEventListener('keyup',   e => { keys[e.code] = false; });

// ── Game Start / Menu ──────────────────────────────────────────────────────
async function startGame(mode, level = 1) {
  numPlayers = mode;
  // Mark that the user has played at least once
  localStorage.setItem('hasPlayed', 'true');

  const res  = await fetch('/api/start_game', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ mode, level })
  });
  const data = await res.json();
  sessionId  = data.session_id;

  // Show/hide HUD controls hint for P2
  document.getElementById('hud-p2-controls').style.display =
    mode === 2 ? 'inline' : 'none';

  document.getElementById('hud').style.display        = 'flex';
  canvas.style.display                                = 'block';
  document.getElementById('winOverlay').style.display = 'none';

  won     = false;
  running = true;
  gameLoop();
}

function returnToMenu() {
  running   = false;
  sessionId = null;
  gameState = null;
  won       = false;
  window.location.href = '/';
}

function goToSoloLevel2() {
  running   = false;
  sessionId = null;
  gameState = null;
  won       = false;
  window.location.href = '/solo_level_2?mode=1&level=2';
}

function goToDuoLevel2() {
  running   = false;
  sessionId = null;
  gameState = null;
  won       = false;
  window.location.href = '/duo_level_2?mode=2&level=2';
}

// ── Auto-start from URL param ───────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const mode   = parseInt(params.get('mode'))  || 1;
  const level  = parseInt(params.get('level')) || 1;
  startGame(mode, level);
});

// ── Input Sampling ─────────────────────────────────────────────────────────
function buildInputPayload() {
  const inputs = {
    p1: {
      left:  keys[BINDINGS.p1.left]  || false,
      right: keys[BINDINGS.p1.right] || false,
      jump:  keys[BINDINGS.p1.jump]  || false
    }
  };
  if (numPlayers === 2) {
    inputs.p2 = {
      left:  keys[BINDINGS.p2.left]  || false,
      right: keys[BINDINGS.p2.right] || false,
      jump:  keys[BINDINGS.p2.jump]  || false
    };
  }
  return inputs;
}

// ── Server Tick ────────────────────────────────────────────────────────────
async function tick() {
  if (!sessionId || won) return;

  try {
    const res = await fetch('/api/input', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ session_id: sessionId, inputs: buildInputPayload() })
    });
    const data = await res.json();
    gameState = data;

    if (data.win) {
      won = true;
      document.getElementById('winOverlay').style.display = 'flex';
    }
  } catch (err) {
    console.error('Tick error:', err);
  }
}

// ── Rendering ──────────────────────────────────────────────────────────────
const TILE_COLOR          = '#4a90d9';
const TILE_SHADOW         = '#2a5fa8';
const PLATE_INACTIVE      = '#8e6b00';
const PLATE_ACTIVE        = '#f1c40f';
const DOOR_COLOR          = '#8e44ad';
const GOAL_DOOR_COLOR     = '#c0860a';
const GOAL_COLOR          = '#2ecc71';
const BG_COLOR            = '#0f0e17';
const GRID_COLOR          = '#ffffff08';

function drawBackground() {
  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Subtle grid
  ctx.strokeStyle = GRID_COLOR;
  ctx.lineWidth   = 1;
  for (let x = 0; x < canvas.width; x += 40) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += 40) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
  }
}

function drawTile(tile, color = TILE_COLOR, shadow = TILE_SHADOW) {
  // Shadow/depth strip
  ctx.fillStyle = shadow;
  ctx.fillRect(tile.x, tile.y + tile.h - 6, tile.w, 6);
  // Main tile
  ctx.fillStyle = color;
  ctx.fillRect(tile.x, tile.y, tile.w, tile.h - 6);
}

function drawPressurePlate(plate) {
  const color = plate.active ? PLATE_ACTIVE : PLATE_INACTIVE;
  ctx.fillStyle = color;
  ctx.fillRect(plate.x, plate.y, plate.w, plate.h);

  ctx.font = 'bold 8px Arial';
  if (plate.duo && plate.player) {
    // Show which player owns this plate
    const label = plate.player === 'p1' ? 'P1' : 'P2';
    const playerColor = plate.player === 'p1' ? '#e74c3c' : '#3498db';
    ctx.fillStyle = plate.active ? '#000' : playerColor;
    ctx.fillText(label, plate.x + plate.w / 2 - 4, plate.y + 7);
  } else {
    ctx.fillStyle = '#000';
    ctx.fillText('▼', plate.x + plate.w / 2 - 4, plate.y + 8);
  }
}

function drawGoal(goal) {
  // Glow effect
  const grd = ctx.createRadialGradient(
    goal.x + goal.w / 2, goal.y + goal.h / 2, 4,
    goal.x + goal.w / 2, goal.y + goal.h / 2, goal.w
  );
  grd.addColorStop(0, '#2ecc7188');
  grd.addColorStop(1, '#2ecc7100');
  ctx.fillStyle = grd;
  ctx.fillRect(goal.x - 10, goal.y - 10, goal.w + 20, goal.h + 20);

  // Goal tile
  ctx.fillStyle = GOAL_COLOR;
  ctx.fillRect(goal.x, goal.y, goal.w, goal.h);

  // Star label
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 20px Arial';
  ctx.fillText('🛸', goal.x + goal.w / 2 - 10, goal.y + goal.h / 2 + 8);
}

function drawGoalDoor(door) {
  if (!door) return;
  // Dark gold shadow strip
  ctx.fillStyle = '#7a5200';
  ctx.fillRect(door.x, door.y + door.h - 6, door.w, 6);
  // Gold body
  ctx.fillStyle = GOAL_DOOR_COLOR;
  ctx.fillRect(door.x, door.y, door.w, door.h - 6);
  // Repeating star icons down the barrier
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 13px Arial';
  for (let iy = door.y + 20; iy < door.y + door.h - 10; iy += 36) {
    ctx.fillText('🛸', door.x + 1, iy);
  }
}

function drawGoalPlate(plate) {
  if (!plate || plate.triggered) return;
  ctx.fillStyle = plate.active ? '#ffd700' : '#7a5200';
  ctx.fillRect(plate.x, plate.y, plate.w, plate.h);
  ctx.font = 'bold 8px Arial';
  if (plate.player) {
    // Duo goal plate: show assigned player label
    const label = plate.player === 'p1' ? 'P1' : 'P2';
    const col   = plate.player === 'p1' ? '#e74c3c' : '#3498db';
    ctx.fillStyle = plate.active ? '#000' : col;
    ctx.fillText(label + '★', plate.x + plate.w / 2 - 7, plate.y + 7);
  } else {
    ctx.fillStyle = plate.active ? '#000' : '#fff';
    ctx.fillText('★', plate.x + plate.w / 2 - 4, plate.y + 8);
  }
}

function drawPlayer(p, pid) {
  const PLAYER_W = 32;
  const PLAYER_H = 48;

  // Body
  ctx.fillStyle = p.color;
  ctx.beginPath();
  ctx.roundRect(p.x, p.y + 12, PLAYER_W, PLAYER_H - 12, 6);
  ctx.fill();

  // Head
  ctx.fillStyle = p.color;
  ctx.beginPath();
  ctx.arc(p.x + PLAYER_W / 2, p.y + 12, 14, 0, Math.PI * 2);
  ctx.fill();

  // Eyes
  ctx.fillStyle = '#fff';
  ctx.beginPath();
  ctx.arc(p.x + 10, p.y + 10, 5, 0, Math.PI * 2);
  ctx.arc(p.x + 22, p.y + 10, 5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#222';
  ctx.beginPath();
  ctx.arc(p.x + 11, p.y + 10, 2.5, 0, Math.PI * 2);
  ctx.arc(p.x + 23, p.y + 10, 2.5, 0, Math.PI * 2);
  ctx.fill();

  // Label above head
  ctx.fillStyle = p.color;
  ctx.font = 'bold 11px Segoe UI';
  const label = pid === 'p1' ? 'P1' : 'P2';
  const tw = ctx.measureText(label).width;
  ctx.fillRect(p.x + PLAYER_W / 2 - tw / 2 - 4, p.y - 22, tw + 8, 16);
  ctx.fillStyle = '#fff';
  ctx.fillText(label, p.x + PLAYER_W / 2 - tw / 2, p.y - 10);
}

function render() {
  drawBackground();
  if (!gameState) return;

  const lvl = gameState.level;

  // Draw normal tiles
  for (const tile of lvl.tiles) drawTile(tile);

  // Draw doors only when closed — disappear entirely when triggered
  if (!lvl.doors_open) {
    for (const door of (lvl.doors || [])) {
      drawTile(door, DOOR_COLOR, '#5b2c6f');
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 18px Arial';
      ctx.fillText('🔒', door.x + 1, door.y + door.h / 2 + 6);
    }
  }

  // Draw door pressure plates (brown) — disappear when triggered
  for (const plate of (lvl.pressure_plates || [])) {
    if (!plate.triggered) drawPressurePlate(plate);
  }

  // Draw solo goal plate — disappears when triggered
  if (lvl.goal_plate && !lvl.goal_plate.triggered) drawGoalPlate(lvl.goal_plate);
  // Draw duo goal plates — each disappears when triggered
  for (const gp of (lvl.goal_plates || [])) {
    if (!gp.triggered) drawGoalPlate(gp);
  }

  // Draw goal door OR actual goal depending on lock state
  if (lvl.goal_locked) {
    drawGoalDoor(lvl.goal_door);
  } else {
    drawGoal(lvl.goal);
  }

  // Draw players
  for (const [pid, p] of Object.entries(gameState.players)) drawPlayer(p, pid);

  // Contextual hint text
  if (!lvl.doors_open) {
    ctx.fillStyle = '#ffffff88';
    ctx.font = '13px Segoe UI';
    const doorHint = numPlayers >= 2
      ? '💡 Both players must stand on the yellow plates at the same time!'
      : '💡 Step on the yellow plate to open the door!';
    ctx.fillText(doorHint, 12, 24);
  } else if (lvl.goal_locked) {
    ctx.fillStyle = '#ffffff88';
    ctx.font = '13px Segoe UI';
    const goalHint = numPlayers >= 2
      ? '💡 Both players must stand on their ★ plate at the same time!'
      : '💡 Find the 🛸 plate to reveal the goal!';
    ctx.fillText(goalHint, 12, 24);
  }
}

// ── Game Loop ──────────────────────────────────────────────────────────────
// We run rendering at ~60fps and server ticks at ~30fps
let lastTick = 0;

function gameLoop(ts = 0) {
  if (!running) return;

  render();

  if (ts - lastTick > 33) {  // ~30 ticks/sec
    tick();
    lastTick = ts;
  }

  requestAnimationFrame(gameLoop);
}