"""
injector.py
注入管理器：只生成 Fingerprint 伪装脚本。
"""

import json


class Injector:
    @staticmethod
    def build_fingerprint_script(fingerprint_overrides: dict, special: dict) -> str:
        lines = []
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

        tz = special.get("timezone")
        if tz:
            lines.append(f"""
const OrigDTF = Intl.DateTimeFormat;
Intl.DateTimeFormat = function(loc, opts) {{
    opts = opts || {{}};
    opts.timeZone = "{tz}";
    return new OrigDTF(loc, opts);
}};""")

        battery = special.get("battery")
        if battery and any(v is not None for v in battery.values()):
            filtered_battery = {k: v for k, v in battery.items() if v is not None}
            lines.append(f"navigator.getBattery = () => Promise.resolve({json.dumps(filtered_battery)});")

        devices = special.get("mediaDevices")
        if devices is not None:
            lines.append(f"navigator.mediaDevices.enumerateDevices = () => Promise.resolve({json.dumps(devices)});")

        conn = special.get("connection")
        if conn and any(v is not None and v != "" for v in conn.values()):
            lines.append(f"""
if (navigator.connection) {{
    Object.defineProperties(navigator.connection, {{
        effectiveType: {{ get: () => {json.dumps(conn['effectiveType'])}, configurable: true }},
        rtt: {{ get: () => {conn['rtt']}, configurable: true }},
        downlink: {{ get: () => {conn['downlink']}, configurable: true }}
    }});
}}
""")

        plugins = special.get("plugins", [])
        mime_types = special.get("mimeTypes", [])
        if plugins or mime_types:
            lines.append(f"""
Object.defineProperty(navigator, 'plugins', {{
    get: () => {json.dumps(plugins)},
    configurable: true
}});
Object.defineProperty(navigator, 'mimeTypes', {{
    get: () => {json.dumps(mime_types)},
    configurable: true
}});
""")

        webgl = special.get("webgl")
        if webgl and (webgl.get("vendor") or webgl.get("renderer")):
            vendor = webgl.get("vendor", "")
            renderer = webgl.get("renderer", "")
            lines.append(f"""
if (typeof WebGLRenderingContext !== 'undefined') {{
    const origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {{
        if (p === 37445) return "{vendor}";
        if (p === 37446) return "{renderer}";
        return origGetParam.call(this, p);
    }};
}}
""")

        script_body = "\n".join(lines)
        return f"""
(function() {{
    'use strict';
    if (window.__bl_fingerprint_installed) return;
    window.__bl_fingerprint_installed = true;
    {script_body}
    console.log('[BrowserLab] Fingerprint script injected.');
}})();
"""
