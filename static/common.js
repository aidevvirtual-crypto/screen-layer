// Shared by screen.html and control.html: websocket + clock sync, video sync, drawing the table.
const SL = (() => {
  let ws, offset = 0, samples = [], handlers = [], hello = null;
  const st = { state: null };

  function send(m) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); }

  function connect(helloMsg, onMsg) {
    hello = helloMsg; handlers.push(onMsg);
    open();
    // clock sync: fast at start, then every 2s
    let n = 0;
    (function ping() { send({ t: 'ping', c: Date.now() }); setTimeout(ping, ++n < 10 ? 150 : 2000); })();
  }

  function open() {
    ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
    ws.onopen = () => send(typeof hello === 'function' ? hello() : hello);
    ws.onclose = () => setTimeout(open, 1000);
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.t === 'pong') {
        const now = Date.now(), rtt = now - m.c;
        samples.push({ rtt, off: m.s - (m.c + rtt / 2) });
        if (samples.length > 15) samples.shift();
        offset = samples.reduce((a, b) => (b.rtt < a.rtt ? b : a)).off; // lowest-latency sample wins
        return;
      }
      if (m.t === 'state') st.state = m;
      handlers.forEach(h => h(m));
    };
  }

  const serverNow = () => Date.now() + offset;

  function targetTime(video) {
    const p = st.state.playback, dur = video.duration;
    let t = p.pos + (p.playing ? Math.max(0, serverNow() - p.at) / 1000 : 0);
    return ((t % dur) + dur) % dur;
  }

  // Keep <video> locked to the server clock: nudge playbackRate for small drift, seek for big drift.
  function syncVideo(video) {
    const S = st.state;
    if (!S || !video.duration || isNaN(video.duration)) return;
    const target = targetTime(video), dur = video.duration;
    if (!S.playback.playing || serverNow() < S.playback.at) {
      if (!video.paused) video.pause();
      if (Math.abs(video.currentTime - target) > 0.04) video.currentTime = target;
      return;
    }
    if (video.paused) video.play().catch(() => {});
    let d = target - video.currentTime;
    if (d > dur / 2) d -= dur; if (d < -dur / 2) d += dur;
    if (Math.abs(d) > 0.4) { video.currentTime = (target + 0.08) % dur; video.playbackRate = 1; }
    else if (Math.abs(d) < 0.015) video.playbackRate = 1;
    else video.playbackRate = Math.min(1.08, Math.max(0.92, 1 + d * 1.5));
  }

  // Draw everything that lives on the table, in table cm coordinates (caller sets the transform).
  function drawTable(ctx, video, px) {
    const S = st.state; if (!S) return;
    const c = S.content;
    if (video.videoWidth) {
      const h = c.w * video.videoHeight / video.videoWidth;
      ctx.save(); ctx.translate(c.x, c.y); ctx.rotate(c.a);
      ctx.drawImage(video, -c.w / 2, -h / 2, c.w, h);
      ctx.restore();
    }
    if (S.grid) drawGrid(ctx, S.table, px);
  }

  // Calibration grid: 5cm cells, labels A1.., diagonals across the whole table (straight lines prove alignment).
  function drawGrid(ctx, T, px) {
    const cell = 5;
    ctx.save();
    ctx.lineWidth = px * 1.5; ctx.strokeStyle = 'rgba(255,255,255,.8)'; ctx.fillStyle = 'rgba(255,255,255,.9)';
    ctx.font = `bold ${cell * 0.3}px sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (let x = 0, i = 0; x < T.w; x += cell, i++)
      for (let y = 0, j = 0; y < T.h; y += cell, j++) {
        ctx.fillStyle = `hsla(${(i * 25 + j * 15) % 360},70%,45%,.45)`;
        ctx.fillRect(x, y, cell, cell);
        ctx.strokeRect(x, y, cell, cell);
        ctx.beginPath(); ctx.arc(x + cell / 2, y + cell / 2, cell * 0.35, 0, 7); ctx.stroke();
        ctx.fillStyle = '#fff';
        ctx.fillText(String.fromCharCode(65 + (i % 26)) + (j + 1), x + cell / 2, y + cell / 2);
      }
    ctx.lineWidth = px * 3; ctx.strokeStyle = '#fff';
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(T.w, T.h); ctx.moveTo(T.w, 0); ctx.lineTo(0, T.h); ctx.stroke();
    ctx.restore();
  }

  return { connect, send, serverNow, syncVideo, drawTable, get state() { return st.state; } };
})();
