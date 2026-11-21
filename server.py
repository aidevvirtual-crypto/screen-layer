"""Screen Layer server: one video spread across many screens lying on a table.

Run:  python3 server.py --video VID.mp4 [--camera 0 | --camera http://phone-ip:8080/video] [--table 60x40] [--https]
Open: http://<this-ip>:8000/          on every phone/tablet (screen)
      http://<this-ip>:8000/control   on the laptop (control panel)
"""
import argparse
import asyncio
import glob
import json
import math
import os
import socket
import ssl
import subprocess
import time

from aiohttp import web, WSMsgType

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
DEFAULT_CM_PER_PX = 0.017  # rough phone guess until camera or manual calibration
SMOOTH = 0.5               # EMA factor for tracked poses


def now_ms():
    return time.time() * 1000


class App:
    def __init__(self, args):
        self.args = args
        tw, th = (float(v) for v in args.table.lower().split("x"))
        self.table = {"w": tw, "h": th}
        self.devices = {}      # id -> device dict
        self.key_to_id = {}    # persistent browser key -> marker id
        self.next_id = 10
        self.sockets = {}      # ws -> device id or None (control)
        self.content = {"x": tw / 2, "y": th / 2, "w": tw, "a": 0.0}
        self.playback = {"playing": False, "pos": 0.0, "at": now_ms()}
        self.grid = False
        self.dirty = True
        self.tracker = None

    # ---------- state ----------
    def state(self):
        return {
            "t": "state",
            "table": self.table,
            "devices": {i: d for i, d in self.devices.items() if d["online"]},
            "content": self.content,
            "playback": self.playback,
            "grid": self.grid,
            "tracking": self.tracker is not None,
            "calibrated": bool(self.tracker and self.tracker.table_locked),
        }

    def current_pos(self):
        p = self.playback
        return p["pos"] + (max(0, now_ms() - p["at"]) / 1000 if p["playing"] else 0)

    async def broadcast_loop(self):
        while True:
            await asyncio.sleep(1 / 30)
            if not self.dirty or not self.sockets:
                continue
            self.dirty = False
            msg = json.dumps(self.state())
            for ws in list(self.sockets):
                if not ws.closed:
                    await ws.send_str(msg)

    # ---------- tracking ----------
    def apply_detections(self, dets):
        for det in dets:
            d = self.devices.get(det["id"])
            if not d or not d["online"] or not d["markerOn"]:
                continue  # only trust a marker while that device is actually showing it
            if d["tracked"] < now_ms() - 1000:  # first sighting after a while: jump, don't smooth
                d["x"], d["y"], d["a"] = det["x"], det["y"], det["a"]
            else:
                da = math.atan2(math.sin(det["a"] - d["a"]), math.cos(det["a"] - d["a"]))
                d["x"] += (det["x"] - d["x"]) * SMOOTH
                d["y"] += (det["y"] - d["y"]) * SMOOTH
                d["a"] += da * SMOOTH
            if d["markerPx"] and not d["manualSize"]:
                k = det["side"] / d["markerPx"]
                d["cmPerPx"] += (k - d["cmPerPx"]) * (SMOOTH if d["tracked"] else 1)
            d["tracked"] = now_ms()
            self.dirty = True

    # ---------- websocket ----------
    async def ws_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        self.sockets[ws] = None
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                m = json.loads(msg.data)
                reply = self.handle(ws, m)
                if reply:
                    await ws.send_str(json.dumps(reply))
        finally:
            did = self.sockets.pop(ws, None)
            if did in self.devices and not any(v == did for v in self.sockets.values()):
                self.devices[did]["online"] = False
                self.dirty = True
        return ws

    def handle(self, ws, m):
        t = m.get("t")
        if t == "ping":
            return {"t": "pong", "c": m["c"], "s": now_ms()}

        if t == "hello" and m.get("role") == "screen":
            key = m.get("key") or str(id(ws))
            did = self.key_to_id.get(key)
            if did is None:
                did = self.key_to_id[key] = self.next_id
                self.next_id += 1
                n = len(self.devices)
                self.devices[did] = {
                    "id": did, "x": self.table["w"] / 2 + (n % 3 - 1) * 12,
                    "y": self.table["h"] / 2 + (n // 3) * 10, "a": 0.0,
                    "cmPerPx": DEFAULT_CM_PER_PX, "manualSize": False,
                    "vw": 0, "vh": 0, "markerOn": False, "markerPx": 0, "tracked": 0,
                }
            d = self.devices[did]
            d.update(online=True, vw=m.get("vw", 0), vh=m.get("vh", 0))
            self.sockets[ws] = did
            self.dirty = True
            return {"t": "welcome", "id": did}

        if t == "hello":  # control panel
            self.dirty = True
            return None

        did = self.sockets.get(ws)
        d = self.devices.get(did)
        if t == "size" and d:
            d.update(vw=m["vw"], vh=m["vh"])
        elif t == "marker" and d:
            d.update(markerOn=bool(m["on"]), markerPx=m.get("px", 0))
        elif t == "screenWidth" and d:  # manual calibration: physical width of the viewport in cm
            if m.get("cm"):
                d.update(cmPerPx=float(m["cm"]) / d["vw"], manualSize=True)
            else:
                d["manualSize"] = False
        elif t == "pose":  # from control panel (manual placement)
            dev = self.devices.get(int(m["id"]))
            if dev:
                for k in ("x", "y", "a"):
                    if k in m:
                        dev[k] = float(m[k])
        elif t == "content":
            self.content.update({k: float(m[k]) for k in ("x", "y", "w", "a") if k in m})
        elif t == "play":
            self.playback = {"playing": True, "pos": self.current_pos(), "at": now_ms() + 300}
        elif t == "pause":
            self.playback = {"playing": False, "pos": self.current_pos(), "at": now_ms()}
        elif t == "seek":
            self.playback = {"playing": self.playback["playing"], "pos": float(m["pos"]), "at": now_ms() + 300}
        elif t == "grid":
            self.grid = bool(m["on"])
        else:
            return None
        self.dirty = True
        return None

    # ---------- http ----------
    async def page(self, request, name):
        return web.FileResponse(os.path.join(STATIC, name))

    async def video(self, request):
        return web.FileResponse(self.args.video)

    async def marker(self, request):
        from tracker import marker_png
        mid = int(request.match_info["id"])
        return web.Response(body=marker_png(mid), content_type="image/png",
                            headers={"Cache-Control": "max-age=86400"})

    async def cam(self, request):
        if not self.tracker:
            raise web.HTTPNotFound(text="no camera (start with --camera)")
        resp = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
        await resp.prepare(request)
        while True:
            jpg = self.tracker.latest_jpeg()
            if jpg:
                await resp.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
            await asyncio.sleep(0.1)

    async def on_startup(self, app):
        app["bcast"] = asyncio.create_task(self.broadcast_loop())
        if self.args.camera is not None:
            from tracker import Tracker
            loop = asyncio.get_running_loop()
            self.tracker = Tracker(self.args.camera, self.table["w"], self.table["h"],
                                   lambda dets: loop.call_soon_threadsafe(self.apply_detections, dets))
            self.tracker.start()


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no packet is sent; just picks the LAN interface
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def ssl_context():
    cert_dir = os.path.join(HERE, "certs")
    crt, key = os.path.join(cert_dir, "cert.pem"), os.path.join(cert_dir, "key.pem")
    if not os.path.exists(crt):
        os.makedirs(cert_dir, exist_ok=True)
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "825",
                        "-keyout", key, "-out", crt, "-subj", "/CN=screen-layer"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(crt, key)
    return ctx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", help="video file to play (default: first *.mp4 here)")
    ap.add_argument("--camera", help="camera index (0) or stream URL; omit for manual mode")
    ap.add_argument("--table", default="60x40", help="table area WxH in cm (between table marker centers)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--https", action="store_true", help="self-signed HTTPS (needed for motion sensor / wake lock)")
    args = ap.parse_args()
    if not args.video:
        vids = sorted(glob.glob(os.path.join(HERE, "*.mp4")))
        if not vids:
            ap.error("no --video given and no *.mp4 found")
        args.video = vids[0]

    a = App(args)
    app = web.Application()
    app.router.add_get("/", lambda r: a.page(r, "screen.html"))
    app.router.add_get("/control", lambda r: a.page(r, "control.html"))
    app.router.add_get("/markers", lambda r: a.page(r, "markers.html"))
    app.router.add_get("/ws", a.ws_handler)
    app.router.add_get("/video", a.video)
    app.router.add_get("/marker/{id}.png", a.marker)
    app.router.add_get("/cam.mjpg", a.cam)
    app.router.add_static("/static", STATIC)
    app.on_startup.append(a.on_startup)

    scheme = "https" if args.https else "http"
    base = f"{scheme}://{lan_ip()}:{args.port}"
    print(f"\n  video   : {args.video}\n  screens : {base}/\n  control : {base}/control"
          f"\n  markers : {base}/markers\n  mode    : {'camera ' + str(args.camera) if args.camera else 'manual (no camera)'}\n")
    web.run_app(app, port=args.port, ssl_context=ssl_context() if args.https else None, print=None)


if __name__ == "__main__":
    main()
