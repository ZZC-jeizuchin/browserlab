"""
injector.py
注入管理器：生成综合指纹伪装脚本，移除了阻止更新的防重复标志。
"""

import json

class Injector:
    @staticmethod
    def build_fingerprint_script(fingerprint_overrides: dict, special: dict) -> str:
        lines = []

        # ---- 1. 简单属性覆盖 (defineProperty) ----
        for path, value in fingerprint_overrides.items():
            js_val = json.dumps(value)
            parts = path.split('.')
            if len(parts) == 2:
                obj, prop = parts[0], parts[1]
                lines.append(
                    f"try {{ Object.defineProperty({obj}, '{prop}', {{ get: () => {js_val}, configurable: true }}); }} catch(e) {{}}"
                )
            elif len(parts) == 3:
                obj_path = '.'.join(parts[:-1])
                prop = parts[-1]
                lines.append(
                    f"try {{ if ({obj_path}) Object.defineProperty({obj_path}, '{prop}', {{ get: () => {js_val}, configurable: true }}); }} catch(e) {{}}"
                )
            elif len(parts) == 4 and parts[0] == 'visualViewport':
                lines.append(
                    f"if (window.visualViewport) Object.defineProperty(visualViewport, '{parts[-1]}', {{ get: () => {js_val}, configurable: true }});"
                )

        # ---- 2. 时区 ----
        tz = special.get("timezone")
        if tz:
            lines.append(f"""
const OrigDTF = Intl.DateTimeFormat;
Intl.DateTimeFormat = function(loc, opts) {{
    opts = opts || {{}};
    opts.timeZone = "{tz}";
    return new OrigDTF(loc, opts);
}};""")

        # ---- 3. 电池 ----
        battery = special.get("battery")
        if battery and any(v is not None for v in battery.values()):
            filtered_battery = {k: v for k, v in battery.items() if v is not None}
            lines.append(f"navigator.getBattery = () => Promise.resolve({json.dumps(filtered_battery)});")

        # ---- 4. 媒体设备 ----
        devices = special.get("mediaDevices")
        if devices is not None:
            lines.append(f"navigator.mediaDevices.enumerateDevices = () => Promise.resolve({json.dumps(devices)});")

        # ---- 5. 网络连接 ----
        conn = special.get("connection")
        if conn:
            lines.append(f"""
if (navigator.connection) {{
    Object.defineProperties(navigator.connection, {{
        effectiveType: {{ get: () => {json.dumps(conn['effectiveType'])}, configurable: true }},
        rtt: {{ get: () => {conn['rtt']}, configurable: true }},
        downlink: {{ get: () => {conn['downlink']}, configurable: true }},
        saveData: {{ get: () => {json.dumps(conn['saveData'])}, configurable: true }}
    }});
}}""")

        # ---- 6. 插件和 MIME ----
        plugins = special.get("plugins", [])
        mime_types = special.get("mimeTypes", [])
        if plugins or mime_types:
            lines.append(f"""
Object.defineProperty(navigator, 'plugins', {{ get: () => {json.dumps(plugins)}, configurable: true }});
Object.defineProperty(navigator, 'mimeTypes', {{ get: () => {json.dumps(mime_types)}, configurable: true }});
""")

        # ---- 7. WebGL 深度伪装 ----
        webgl = special.get("webgl")
        if webgl:
            vendor = webgl.get("vendor", "")
            renderer = webgl.get("renderer", "")
            params = webgl.get("params", {})
            if vendor or renderer:
                lines.append(f"""
if (typeof WebGLRenderingContext !== 'undefined') {{
    const origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {{
        if (p === 37445) return "{vendor}";
        if (p === 37446) return "{renderer}";
        return origGetParam.call(this, p);
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        WebGL2RenderingContext.prototype.getParameter = WebGLRenderingContext.prototype.getParameter;
    }}
}}
""")
            param_map = {
                "MAX_TEXTURE_SIZE": 3379,
                "MAX_RENDERBUFFER_SIZE": 34024,
                "MAX_VIEWPORT_DIMS": 3386,
                "MAX_VERTEX_ATTRIBS": 34921,
                "MAX_TEXTURE_IMAGE_UNITS": 34930,
            }
            for pname, pval in params.items():
                if pval and pname in param_map:
                    lines.append(f"""
if (typeof WebGLRenderingContext !== 'undefined') {{
    const origGetParam{pname} = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {{
        if (p === {param_map[pname]}) return {json.dumps(pval)};
        return origGetParam{pname}.call(this, p);
    }};
}}
""")

        # ---- 8. Canvas 噪点 ----
        if special.get("canvas", {}).get("noise", False):
            lines.append("""
(function() {
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
        const ctx = this.getContext('2d');
        if (ctx) {
            const imgData = ctx.getImageData(0, 0, 1, 1);
            imgData.data[0] ^= 1;
            ctx.putImageData(imgData, 0, 0);
        }
        return origToDataURL.apply(this, arguments);
    };
})();""")

        # ---- 9. Audio 指纹固定 ----
        if special.get("audio", {}).get("noise", False):
            lines.append("""
(function() {
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {
        const data = origGetChannelData.call(this, channel);
        for (let i = 0; i < data.length; i++) {
            data[i] += (Math.random() - 0.5) * 1e-6;
        }
        return data;
    };
})();""")

        # ---- 10. 字体隐藏 ----
        fonts = special.get("fonts", [])
        if fonts is not None:
            lines.append("if (document.fonts) document.fonts = [];")
            lines.append(f"Object.defineProperty(document, 'fonts', {{ get: () => {json.dumps(fonts)}, configurable: true }});")

        # ---- 11. 传感器 ----
        sensors = special.get("sensors", {})
        for sname, sval in sensors.items():
            if sval is not None:
                class_name = sname.capitalize()
                lines.append(f"if (typeof {class_name} !== 'undefined') {{ Object.defineProperty(window, '{class_name}', {{ get: () => undefined, configurable: true }}); }}")

        # ---- 12. 外设 ----
        per = special.get("peripherals", {})
        for pname, pval in per.items():
            if pval is not None:
                if pname in ("bluetooth", "usb", "serial", "hid"):
                    lines.append(f"Object.defineProperty(navigator, '{pname}', {{ get: () => undefined, configurable: true }});")
                elif pname == "nfc":
                    lines.append("if (typeof NDEFReader !== 'undefined') { Object.defineProperty(window, 'NDEFReader', { get: () => undefined, configurable: true }); }")
                elif pname == "midi":
                    lines.append("if (navigator.requestMIDIAccess) { navigator.requestMIDIAccess = undefined; }")

        # ---- 13. 存储特性 ----
        storage_feat = special.get("storage_features", {})
        if not storage_feat.get("localStorage", True):
            lines.append("delete window.localStorage;")
        if not storage_feat.get("sessionStorage", True):
            lines.append("delete window.sessionStorage;")
        if not storage_feat.get("indexedDB", True):
            lines.append("delete window.indexedDB;")
        if not storage_feat.get("cacheStorage", True):
            lines.append("delete window.caches;")
        if not storage_feat.get("opfs", False):
            lines.append("if (navigator.storage && navigator.storage.getDirectory) navigator.storage.getDirectory = undefined;")

        # ---- 14. WebAssembly ----
        wasm = special.get("wasm", {})
        if not wasm.get("supported", True):
            lines.append("delete WebAssembly;")

        # ---- 15. 性能内存 ----
        perf_mem = special.get("performance_memory", {})
        if perf_mem:
            js_limit = perf_mem.get("jsHeapSizeLimit", 0)
            total = perf_mem.get("totalJSHeapSize", 0)
            used = perf_mem.get("usedJSHeapSize", 0)
            lines.append(f"""
if (performance.memory) {{
    performance.memory.jsHeapSizeLimit = {js_limit};
    performance.memory.totalJSHeapSize = {total};
    performance.memory.usedJSHeapSize = {used};
}}""")

        # ---- 16. WebDriver ----
        if not special.get("webdriver_flag", True):
            lines.append("Object.defineProperty(navigator, 'webdriver', { get: () => false, configurable: true });")

        # ---- 17. window.chrome ----
        if not special.get("window_chrome", True):
            lines.append("delete window.chrome;")

        # ---- 18. WebRTC 本地 IP ----
        webrtc_ip = special.get("webrtc", {}).get("privateIP", "")
        if webrtc_ip:
            lines.append(f"""
const origRTCPeerConnection = window.RTCPeerConnection;
window.RTCPeerConnection = function(config) {{
    const pc = new origRTCPeerConnection(config);
    const origCreateDataChannel = pc.createDataChannel;
    pc.createDataChannel = function(...args) {{
        const channel = origCreateDataChannel.apply(pc, args);
        pc.onicecandidate = (e) => {{
            if (e.candidate) {{}}
        }};
        return channel;
    }};
    return pc;
}};""")

        script_body = "\n".join(lines)
        return f"""
(function() {{
    'use strict';
    {script_body}
    console.log('[BrowserLab] Fingerprint script injected.');
}})();
"""
