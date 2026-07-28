"""
controller.py
Controller：集成实时指纹采集功能。
"""

import json
from browser import Browser
from ui import UI
from network import Network
from storage import Storage
from session import Session
from fingerprint import Fingerprint
from injector import Injector
from urllib.parse import urlparse


class Controller:
    def __init__(self):
        self.browser = Browser()
        self.network = Network()
        self.storage = Storage()
        self.session = Session()
        self.fingerprint = Fingerprint()
        self.injector = Injector()
        self.ui = UI(self)

        self.browser.set_domain_visit_callback(self._on_domain_visited)

        # 启动时自动打开浏览器（空白页）
        self.open_browser("about:blank")

    def run(self):
        self.ui.run()

    def _safe_call(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.ui.log(f"[错误] {e}")
            return None

    # ---------- 辅助 ----------
    def _get_current_domain(self):
        url = self._safe_call(self.browser.get_url)
        if url:
            parsed = urlparse(url)
            return parsed.hostname or ""
        return ""

    def _apply_injection(self):
        if not self.browser.is_running():
            return
        fingerprint_overrides = self.fingerprint.get_injection_overrides()
        special = self.fingerprint.get_special_injection_data()
        script = self.injector.build_fingerprint_script(fingerprint_overrides, special)
        self._safe_call(self.browser.inject_on_new_document, script)

    # ---------- 浏览器生命周期 ----------
    def open_browser(self, url="about:blank"):
        self._safe_call(self.browser.open, url)
        if self.browser.is_running():
            self._safe_call(self.network.apply_to_browser, self.browser)
            self._apply_injection()

    def close_browser(self):
        self._safe_call(self.browser.close)

    def browser_running(self):
        return self.browser.is_running()

    # ---------- 页面控制 ----------
    def load_url(self, url):
        self._safe_call(self.browser.load_url, url)
        self._apply_injection()

    def reload(self):
        self._apply_injection()
        self._safe_call(self.browser.reload)

    def back(self):
        self._safe_call(self.browser.back)

    def forward(self):
        self._safe_call(self.browser.forward)

    def execute_js(self, script):
        result = self._safe_call(self.browser.execute_js, script)
        if result is not None:
            self.ui.log(f"JS 返回值: {result}")
        return result

    def get_title(self):
        return self._safe_call(self.browser.get_title) or ""

    def get_url(self):
        return self._safe_call(self.browser.get_url) or ""

    def new_tab(self, url="about:blank"):
        self._safe_call(self.browser.new_tab, url)
        if self.browser.is_running():
            self._safe_call(self.network.apply_to_browser, self.browser)
            self._apply_injection()

    def close_tab(self):
        self._safe_call(self.browser.close_tab)

    def get_tab_count(self) -> int:
        tabs = self._safe_call(self.browser.get_tabs)
        if tabs:
            return len([t for t in tabs if t.get("type") == "page"])
        return 0

    # ---------- 网络身份 ----------
    def set_user_agent(self, ua):
        self.network.set_user_agent(ua)
        if self.browser.is_running():
            self._safe_call(self.browser.set_user_agent, ua)
        self.ui.log(f"User-Agent 已设置为: {ua}")

    def set_header(self, key, value):
        self.network.set_header(key, value)
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, self.network.get_headers())
        self.ui.log(f"请求头已设置: {key}: {value}")

    def remove_header(self, key):
        self.network.remove_header(key)
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, self.network.get_headers())
        self.ui.log(f"请求头已移除: {key}")

    def clear_headers(self):
        self.network.clear_headers()
        if self.browser.is_running():
            self._safe_call(self.browser.set_extra_headers, {})
        self.ui.log("所有自定义请求头已清除。")

    # ---------- Storage 管理 ----------
    def get_storage_domains(self):
        return self.storage.get_all_domains()

    def get_cookies_for_domain(self, domain: str) -> dict:
        if not self.browser.is_running():
            return {}
        all_cookies = self._safe_call(self.browser.get_all_cookies) or []
        result = {}
        for c in all_cookies:
            cookie_domain = c.get("domain", "").lstrip(".")
            if cookie_domain == domain or cookie_domain.endswith("." + domain) or domain.endswith(cookie_domain):
                result[c["name"]] = c["value"]
        return result

    def set_cookie(self, domain: str, name: str, value: str):
        self._safe_call(self.browser.set_cookie, name, value, domain)
        self.ui.log(f"Cookie [{domain}] {name} = {value}")

    def delete_cookie(self, domain: str, name: str):
        self._safe_call(self.browser.delete_cookies, name, domain)

    def clear_cookies(self, domain: str):
        cookies = self.get_cookies_for_domain(domain)
        for name in cookies:
            self._safe_call(self.browser.delete_cookies, name, domain)

    def get_local_storage_for_domain(self, domain: str) -> dict:
        if not self.browser.is_running():
            return {}
        origin = f"https://{domain}"
        return self._safe_call(self.browser.get_all_local_storage, origin) or {}

    def set_local_storage_item(self, domain: str, key: str, value: str):
        if not self.browser.is_running():
            return
        origin = f"https://{domain}"
        self._safe_call(self.browser.set_local_storage_item, origin, key, value)

    def delete_local_storage_item(self, domain: str, key: str):
        if not self.browser.is_running():
            return
        origin = f"https://{domain}"
        self._safe_call(self.browser.remove_local_storage_item, origin, key)

    def clear_local_storage(self, domain: str):
        if not self.browser.is_running():
            return
        origin = f"https://{domain}"
        self._safe_call(self.browser.clear_local_storage, origin)

    # ---------- 域名自动记录 ----------
    def _on_domain_visited(self, domain: str):
        self.storage.add_domain(domain)
        self.ui.log(f"域名已记录: {domain}")

    # ---------- Fingerprint 管理 ----------
    def get_fingerprint_properties(self) -> dict:
        return self.fingerprint.get_all_properties()

    def set_fingerprint_property(self, key: str, value):
        self.fingerprint.set_property(key, value)
        self.ui.log(f"指纹属性 {key} 已设置为 {value}")

    def apply_fingerprint_preset(self, preset_name: str) -> bool:
        success = self.fingerprint.apply_preset(preset_name)
        if success:
            self.ui.log(f"已应用身份模板: {preset_name}")
            if self.browser.is_running():
                self._apply_injection()
        return success

    def apply_fingerprint_now(self):
        if self.browser.is_running():
            self._apply_injection()
            self.ui.log("指纹配置已重新注入")

    def refresh_fingerprint_from_browser(self):
        """通过 CDP 执行 JS 获取浏览器当前真实指纹，并更新 Fingerprint 对象"""
        if not self.browser.is_running():
            return

        js_code = """
        (function() {
            const result = {};
            // 1. 用户代理与平台
            result['navigator.platform'] = navigator.platform;
            result['navigator.vendor'] = navigator.vendor;
            result['navigator.vendorSub'] = navigator.vendorSub;
            result['navigator.productSub'] = navigator.productSub;
            result['navigator.appName'] = navigator.appName;
            result['navigator.appCodeName'] = navigator.appCodeName;
            result['navigator.appVersion'] = navigator.appVersion;
            result['navigator.oscpu'] = navigator.oscpu || '';
            result['navigator.buildID'] = navigator.buildID || '';
            result['navigator.webdriver'] = navigator.webdriver;
            result['navigator.userAgent'] = navigator.userAgent;
            // 2. 屏幕与显示
            result['screen.width'] = screen.width;
            result['screen.height'] = screen.height;
            result['screen.availWidth'] = screen.availWidth;
            result['screen.availHeight'] = screen.availHeight;
            result['screen.colorDepth'] = screen.colorDepth;
            result['screen.pixelDepth'] = screen.pixelDepth;
            result['devicePixelRatio'] = window.devicePixelRatio;
            result['innerWidth'] = window.innerWidth;
            result['innerHeight'] = window.innerHeight;
            try { result['screen.orientation.type'] = screen.orientation.type; } catch(e) { result['screen.orientation.type'] = ''; }
            try { result['screen.orientation.angle'] = screen.orientation.angle; } catch(e) { result['screen.orientation.angle'] = 0; }
            // 3. 电池与网络
            result['battery.charging'] = null;
            result['battery.level'] = null;
            result['battery.chargingTime'] = null;
            result['battery.dischargingTime'] = null;
            const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            if (conn) {
                result['navigator.connection.effectiveType'] = conn.effectiveType;
                result['navigator.connection.rtt'] = conn.rtt;
                result['navigator.connection.downlink'] = conn.downlink;
                result['navigator.connection.saveData'] = conn.saveData;
            }
            // 4. 硬件与内存
            result['navigator.hardwareConcurrency'] = navigator.hardwareConcurrency;
            result['navigator.deviceMemory'] = navigator.deviceMemory;
            result['navigator.maxTouchPoints'] = navigator.maxTouchPoints;
            // 5. 图形与 GPU
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (gl) {
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                result['webgl.vendor'] = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : '';
                result['webgl.renderer'] = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : '';
            }
            result['webgl2.supported'] = !!window.WebGL2RenderingContext;
            // 6. 音频指纹
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const ctx = new AudioContext();
                result['audio.sampleRate'] = ctx.sampleRate;
                result['audio.state'] = ctx.state;
            }
            // 7. 字体检测
            result['fonts.installed'] = [];
            // 8. 插件与 MIME
            result['navigator.plugins'] = Array.from(navigator.plugins).map(p => p.name);
            result['navigator.mimeTypes'] = Array.from(navigator.mimeTypes).map(m => m.type);
            // 9. 国际化
            result['navigator.language'] = navigator.language;
            result['navigator.languages'] = navigator.languages;
            result['timezone'] = Intl.DateTimeFormat().resolvedOptions().timeZone;
            // 10. 传感器与设备
            result['sensors.accelerometer'] = !!window.Accelerometer;
            result['sensors.gyroscope'] = !!window.Gyroscope;
            result['sensors.magnetometer'] = !!window.Magnetometer;
            result['sensors.ambientLight'] = !!window.AmbientLightSensor;
            result['sensors.proximity'] = !!window.ProximitySensor;
            result['mediaDevices'] = [];
            // 11. 外设与连接
            result['navigator.bluetooth'] = !!navigator.bluetooth;
            result['navigator.usb'] = !!navigator.usb;
            result['navigator.serial'] = !!navigator.serial;
            result['navigator.hid'] = !!navigator.hid;
            result['nfc.supported'] = !!window.NDEFReader;
            result['midi.supported'] = !!navigator.requestMIDIAccess;
            // 12. 存储与缓存
            result['storage.localStorage'] = !!window.localStorage;
            result['storage.sessionStorage'] = !!window.sessionStorage;
            result['storage.indexedDB'] = !!window.indexedDB;
            result['storage.cacheStorage'] = !!window.caches;
            result['storage.opfs'] = !!(navigator.storage && navigator.storage.getDirectory);
            result['navigator.cookieEnabled'] = navigator.cookieEnabled;
            // 13. 性能与内存
            if (performance.memory) {
                result['performance.memory.jsHeapSizeLimit'] = performance.memory.jsHeapSizeLimit;
                result['performance.memory.totalJSHeapSize'] = performance.memory.totalJSHeapSize;
                result['performance.memory.usedJSHeapSize'] = performance.memory.usedJSHeapSize;
            }
            // 14. 自动化检测
            result['navigator.webdriver'] = navigator.webdriver;
            result['window.chrome'] = !!window.chrome;
            // 15. 其他 Navigator 属性
            result['navigator.onLine'] = navigator.onLine;
            result['navigator.doNotTrack'] = navigator.doNotTrack || '';
            result['navigator.javaEnabled'] = typeof navigator.javaEnabled === 'function' ? navigator.javaEnabled() : false;
            result['navigator.pdfViewerEnabled'] = navigator.pdfViewerEnabled;
            result['navigator.virtualKeyboard'] = !!navigator.virtualKeyboard;
            // 16. 窗口与文档环境
            result['outerWidth'] = window.outerWidth;
            result['outerHeight'] = window.outerHeight;
            result['screenX'] = window.screenX;
            result['screenY'] = window.screenY;
            result['scrollX'] = window.scrollX;
            result['scrollY'] = window.scrollY;
            result['visualViewport.width'] = window.visualViewport ? visualViewport.width : 0;
            result['crossOriginIsolated'] = window.crossOriginIsolated;
            result['isSecureContext'] = window.isSecureContext;
            result['document.hidden'] = document.hidden;
            result['document.visibilityState'] = document.visibilityState;
            // 17. WebRTC
            result['webrtc.privateIP'] = '';
            // 18. Canvas 指纹
            result['canvas.noise'] = false;
            // 19. Audio 指纹
            result['audio.noise'] = false;
            // 20. WebAssembly
            result['wasm.supported'] = !!window.WebAssembly;
            result['wasm.simd'] = false;
            result['wasm.threads'] = false;
            // 21. 共享内存
            result['crossOriginIsolated'] = window.crossOriginIsolated;
            // 22. 媒体能力
            result['mediaCapabilities.h264'] = false;
            result['mediaCapabilities.h265'] = false;
            result['mediaCapabilities.vp8'] = false;
            result['mediaCapabilities.vp9'] = false;
            result['mediaCapabilities.av1'] = false;
            return JSON.stringify(result);
        })();
        """

        raw_result = self._safe_call(self.browser.execute_js, js_code)
        if not raw_result:
            self.ui.log("无法获取浏览器指纹")
            return

        try:
            data = json.loads(raw_result)
        except json.JSONDecodeError:
            self.ui.log("指纹数据解析失败")
            return

        for key, value in data.items():
            self.fingerprint.set_property(key, value)

        self.ui.log("已从浏览器读取真实指纹")

    def shutdown(self):
        pass
