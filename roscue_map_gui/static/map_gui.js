const state = {
    map: null,
    mapCanvas: null,
    mapCtx: null,
    offscreen: null,
    offscreenCtx: null,
    points: [],
    robotPoses: {},
    view: {
        scale: 1,
        offsetX: 0,
        offsetY: 0,
        userChanged: false,
    },
    dragging: false,
    dragStart: null,
};

function $(id) { return document.getElementById(id); }

function log(message) {
    const el = $('log-box');
    const now = new Date().toLocaleTimeString();
    el.textContent = `[${now}] ${message}\n` + el.textContent;
}

function setConnection(connected, text) {
    const el = $('connection-status');
    el.className = 'status-badge ' + (connected ? 'connected' : 'disconnected');
    el.textContent = text;
}

function init() {
    state.mapCanvas = $('map-canvas');
    state.mapCtx = state.mapCanvas.getContext('2d');
    state.offscreen = document.createElement('canvas');
    state.offscreenCtx = state.offscreen.getContext('2d');

    window.addEventListener('resize', () => {
        resizeCanvas();
        fitMap(false);
        draw();
    });

    $('view-reset').addEventListener('click', () => {
        fitMap(true);
        draw();
    });

    for (const id of ['show-clicked', 'show-random', 'show-completed', 'show-robots']) {
        $(id).addEventListener('change', draw);
    }

    state.mapCanvas.addEventListener('mousemove', onMouseMove);
    state.mapCanvas.addEventListener('click', onCanvasClick);
    state.mapCanvas.addEventListener('wheel', onWheel, { passive: false });
    state.mapCanvas.addEventListener('mousedown', onMouseDown);
    state.mapCanvas.addEventListener('mouseup', onMouseUp);
    state.mapCanvas.addEventListener('mouseleave', () => { state.dragging = false; });

    resizeCanvas();
    loadSnapshot();
    connectEvents();
}

async function loadSnapshot() {
    try {
        const resp = await fetch('/api/snapshot');
        const data = await resp.json();
        applySnapshot(data);
        setConnection(true, '연결됨');
    } catch (e) {
        setConnection(false, '연결 실패');
        log('snapshot error: ' + e.message);
    }
}

function connectEvents() {
    const es = new EventSource('/events');

    es.addEventListener('open', () => setConnection(true, '실시간 연결'));
    es.addEventListener('error', () => setConnection(false, '재연결 중'));

    es.addEventListener('snapshot', (ev) => applySnapshot(JSON.parse(ev.data)));
    es.addEventListener('map', (ev) => applyMap(JSON.parse(ev.data)));
    es.addEventListener('robot_pose', (ev) => {
        const data = JSON.parse(ev.data);
        state.robotPoses[data.robot_name] = data;
        updateRobotInfo();
        draw();
    });
    es.addEventListener('points', (ev) => {
        const data = JSON.parse(ev.data);
        state.points = data.points || [];
        updatePointCounts();
        draw();
    });
    es.addEventListener('status', (ev) => applyStatus(JSON.parse(ev.data)));
}

function applySnapshot(data) {
    if (data.status) applyStatus(data.status);
    if (data.map) applyMap(data.map);
    state.robotPoses = data.robot_poses || {};
    state.points = data.points || [];
    updateRobotInfo();
    updatePointCounts();
    draw();
}

function applyStatus(status) {
    $('ros-domain').textContent = status.ros_domain_id ?? '-';
    $('map-topic').textContent = status.map_topic ?? '-';
    $('clicked-topic').textContent = status.clicked_point_topic ?? '-';
    const dbOk = status.db_available ? '연결됨' : '대기/오류';
    $('db-status').textContent = `${dbOk} ${status.last_db_error ? '(' + status.last_db_error + ')' : ''}`;
}

function applyMap(map) {
    state.map = map;
    buildOffscreenMap(map);
    $('map-empty').style.display = 'none';
    $('map-size').textContent = `${map.width} x ${map.height}`;
    $('map-resolution').textContent = `${Number(map.resolution).toFixed(3)} m/cell`;
    $('map-origin').textContent = `(${Number(map.origin_x).toFixed(2)}, ${Number(map.origin_y).toFixed(2)})`;
    fitMap(false);
    draw();
}

function buildOffscreenMap(map) {
    const width = map.width;
    const height = map.height;
    const bytes = base64ToUint8(map.gray);

    state.offscreen.width = width;
    state.offscreen.height = height;

    const image = state.offscreenCtx.createImageData(width, height);
    for (let i = 0; i < bytes.length; i++) {
        const g = bytes[i];
        const j = i * 4;
        image.data[j] = g;
        image.data[j + 1] = g;
        image.data[j + 2] = g;
        image.data[j + 3] = 255;
    }
    state.offscreenCtx.putImageData(image, 0, 0);
}

function base64ToUint8(b64) {
    const bin = atob(b64);
    const len = bin.length;
    const arr = new Uint8Array(len);
    for (let i = 0; i < len; i++) arr[i] = bin.charCodeAt(i);
    return arr;
}

function resizeCanvas() {
    const rect = state.mapCanvas.parentElement.getBoundingClientRect();
    state.mapCanvas.width = Math.max(300, Math.floor(rect.width));
    state.mapCanvas.height = Math.max(300, Math.floor(rect.height));
}

function fitMap(force) {
    if (!state.map) return;
    if (state.view.userChanged && !force) return;

    const sx = state.mapCanvas.width / state.map.width;
    const sy = state.mapCanvas.height / state.map.height;
    const scale = Math.min(sx, sy) * 0.96;
    state.view.scale = scale;
    state.view.offsetX = (state.mapCanvas.width - state.map.width * scale) / 2;
    state.view.offsetY = (state.mapCanvas.height - state.map.height * scale) / 2;
    state.view.userChanged = false;
}

function mapToPixel(x, y) {
    const m = state.map;
    if (!m) return null;
    const px = (x - m.origin_x) / m.resolution;
    const py = m.height - ((y - m.origin_y) / m.resolution);
    return { px, py };
}

function pixelToMap(px, py) {
    const m = state.map;
    if (!m) return null;
    return {
        x: m.origin_x + px * m.resolution,
        y: m.origin_y + (m.height - py) * m.resolution,
    };
}

function mapToScreen(x, y) {
    const p = mapToPixel(x, y);
    if (!p) return null;
    return {
        x: state.view.offsetX + p.px * state.view.scale,
        y: state.view.offsetY + p.py * state.view.scale,
    };
}

function screenToMap(sx, sy) {
    if (!state.map) return null;
    const px = (sx - state.view.offsetX) / state.view.scale;
    const py = (sy - state.view.offsetY) / state.view.scale;
    if (px < 0 || py < 0 || px >= state.map.width || py >= state.map.height) return null;
    return pixelToMap(px, py);
}

function eventToCanvasXY(e) {
    const rect = state.mapCanvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left) * (state.mapCanvas.width / rect.width),
        y: (e.clientY - rect.top) * (state.mapCanvas.height / rect.height),
    };
}

function onMouseMove(e) {
    const c = eventToCanvasXY(e);
    const p = screenToMap(c.x, c.y);
    if (p) {
        $('mouse-x').textContent = p.x.toFixed(3);
        $('mouse-y').textContent = p.y.toFixed(3);
    } else {
        $('mouse-x').textContent = '-';
        $('mouse-y').textContent = '-';
    }

    if (state.dragging && state.dragStart) {
        const dx = c.x - state.dragStart.x;
        const dy = c.y - state.dragStart.y;
        state.view.offsetX += dx;
        state.view.offsetY += dy;
        state.dragStart = c;
        state.view.userChanged = true;
        draw();
    }
}

function onMouseDown(e) {
    if (e.button === 1 || e.shiftKey) {
        state.dragging = true;
        state.dragStart = eventToCanvasXY(e);
        e.preventDefault();
    }
}

function onMouseUp() {
    state.dragging = false;
    state.dragStart = null;
}

function onWheel(e) {
    if (!state.map) return;
    e.preventDefault();
    const c = eventToCanvasXY(e);
    const before = screenToMap(c.x, c.y);
    const factor = e.deltaY < 0 ? 1.15 : 0.87;
    state.view.scale = Math.max(0.05, Math.min(20, state.view.scale * factor));
    if (before) {
        const pix = mapToPixel(before.x, before.y);
        state.view.offsetX = c.x - pix.px * state.view.scale;
        state.view.offsetY = c.y - pix.py * state.view.scale;
    }
    state.view.userChanged = true;
    draw();
}

async function onCanvasClick(e) {
    // shift+drag pan을 위한 click은 무시
    if (e.shiftKey || e.button !== 0) return;
    const c = eventToCanvasXY(e);
    const p = screenToMap(c.x, c.y);
    if (!p) return;

    try {
        const resp = await fetch('/api/clicked_point', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: p.x, y: p.y, z: 0.0 }),
        });
        const data = await resp.json();
        if (resp.ok) log(data.message);
        else log('[FAIL] ' + data.message);
    } catch (err) {
        log('[ERROR] clicked_point: ' + err.message);
    }
}

function draw() {
    const ctx = state.mapCtx;
    if (!ctx) return;
    ctx.clearRect(0, 0, state.mapCanvas.width, state.mapCanvas.height);
    ctx.fillStyle = '#d1d5db';
    ctx.fillRect(0, 0, state.mapCanvas.width, state.mapCanvas.height);

    if (!state.map) return;

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(
        state.offscreen,
        state.view.offsetX,
        state.view.offsetY,
        state.map.width * state.view.scale,
        state.map.height * state.view.scale
    );

    drawGridBorder(ctx);
    drawPoints(ctx);
    if ($('show-robots').checked) drawRobots(ctx);
}

function drawGridBorder(ctx) {
    ctx.save();
    ctx.strokeStyle = '#111827';
    ctx.lineWidth = 1;
    ctx.strokeRect(
        state.view.offsetX,
        state.view.offsetY,
        state.map.width * state.view.scale,
        state.map.height * state.view.scale
    );
    ctx.restore();
}

function pointKind(p) {
    const source = String(p.source || '');
    if (source.includes('random')) return 'random';
    return 'clicked';
}

function drawPoints(ctx) {
    const showClicked = $('show-clicked').checked;
    const showRandom = $('show-random').checked;
    const showCompleted = $('show-completed').checked;

    for (const p of state.points) {
        const kind = pointKind(p);
        const status = String(p.status || '');
        if (kind === 'clicked' && !showClicked) continue;
        if (kind === 'random' && !showRandom) continue;
        if (status === 'completed' && !showCompleted) continue;

        const s = mapToScreen(Number(p.x), Number(p.y));
        if (!s) continue;

        let color = kind === 'random' ? '#2563eb' : '#f59e0b';
        let radius = 5;
        let lineWidth = 2;

        if (status === 'completed') {
            color = '#9ca3af';
            radius = 4;
        } else if (status === 'navigating' || status === 'waiting') {
            color = '#ef4444';
            radius = 7;
        } else if (status === 'local') {
            color = '#f97316';
            radius = 5;
        }

        ctx.save();
        ctx.beginPath();
        ctx.arc(s.x, s.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = '#111827';
        ctx.stroke();

        if (status === 'navigating' || status === 'waiting') {
            ctx.beginPath();
            ctx.arc(s.x, s.y, radius + 6, 0, Math.PI * 2);
            ctx.strokeStyle = color;
            ctx.setLineDash([4, 3]);
            ctx.stroke();
        }

        if (p.order !== null && p.order !== undefined) {
            ctx.font = '11px Arial';
            ctx.fillStyle = '#111827';
            ctx.fillText(String(p.order), s.x + 8, s.y - 8);
        }
        ctx.restore();
    }
}

function drawRobots(ctx) {
    for (const [name, pose] of Object.entries(state.robotPoses)) {
        const s = mapToScreen(Number(pose.x), Number(pose.y));
        if (!s) continue;
        const color = name === 'wf1' ? '#16a34a' : '#9333ea';
        const yaw = Number(pose.yaw || 0);

        ctx.save();
        ctx.translate(s.x, s.y);
        // map yaw는 x축 기준 반시계, canvas는 y축 아래 방향이므로 부호 반전
        ctx.rotate(-yaw);
        ctx.beginPath();
        ctx.moveTo(16, 0);
        ctx.lineTo(-10, -8);
        ctx.lineTo(-10, 8);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#111827';
        ctx.stroke();
        ctx.restore();

        ctx.save();
        ctx.font = 'bold 13px Arial';
        ctx.fillStyle = '#111827';
        ctx.fillText(name.toUpperCase(), s.x + 10, s.y - 12);
        ctx.restore();
    }
}

function updatePointCounts() {
    let clicked = 0;
    let random = 0;
    let completed = 0;
    for (const p of state.points) {
        if (pointKind(p) === 'random') random += 1;
        else clicked += 1;
        if (String(p.status || '') === 'completed') completed += 1;
    }
    $('clicked-count').textContent = clicked;
    $('random-count').textContent = random;
    $('completed-count').textContent = completed;
}

function updateRobotInfo() {
    for (const name of ['wf1', 'wf2']) {
        const pose = state.robotPoses[name];
        const el = $(`${name}-pose`);
        if (!pose) {
            el.textContent = 'pose 대기';
            continue;
        }
        const yawDeg = Number(pose.yaw || 0) * 180 / Math.PI;
        el.textContent = `x=${Number(pose.x).toFixed(2)}, y=${Number(pose.y).toFixed(2)}, yaw=${yawDeg.toFixed(1)}°`;
    }
}

document.addEventListener('DOMContentLoaded', init);
