// ============================================================
// 驾驶舱电台 - 电台数据（直接内联，避免跨 script 的 const 作用域不共享）
// ============================================================
var COCKPIT_RADIO_STATIONS = [
    { name: "广州青少年广播 FM88.0", region: "gd", url: "https://lhttp.qtfm.cn/live/20194/64k.mp3" },
    { name: "广东音乐之声", region: "gd", url: "https://lhttp.qtfm.cn/live/1260/64k.mp3" },
    { name: "羊城交通电台", region: "gd", url: "https://lhttp.qtfm.cn/live/1262/64k.mp3" },
    { name: "茂名交通广播", region: "gd", url: "https://lhttp.qingting.fm/live/20211574/64k.mp3" },
    { name: "两广之声音乐台", region: "gd", url: "https://lhttp.qtfm.cn/live/20500149/64k.mp3" },
    { name: "中国之声", region: "cn", url: "https://lhttp.qtfm.cn/live/15318317/64k.mp3" },
    { name: "上海经典947", region: "cn", url: "https://lhttp.qtfm.cn/live/267/64k.mp3" },
    { name: "第一财经", region: "cn", url: "http://lhttp.qingting.fm/live/276/64k.mp3" },
    { name: "上海新闻广播", region: "cn", url: "http://lhttp.qingting.fm/live/270/64k.mp3" },
    { name: "北京新闻广播", region: "cn", url: "https://lhttp.qtfm.cn/live/339/64k.mp3" },
    { name: "江苏经典流行", region: "cn", url: "https://lhttp.qtfm.cn/live/4938/64k.mp3" },
    { name: "AsiaFM 亚洲粤语台", region: "hmt", url: "https://lhttp.qtfm.cn/live/15318569/64k.mp3" },
    { name: "台湾古典 97.7", region: "hmt", url: "http://59.120.88.155:8000/live.mp3" },
    { name: "中广流行网(台)", region: "hmt", url: "https://n03.rcs.revma.com/aw9uqyxy2tzuv" },
    { name: "BBC World Service", region: "world", url: "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service" },
    { name: "NPR News(美)", region: "world", url: "https://npr-ice.streamguys1.com/live.mp3" },
    { name: "KEXP 西雅图音乐", region: "world", url: "https://kexp-mp3-128.streamguys1.com/kexp128.mp3" },
    { name: "RFI 中文(法广)", region: "world", url: "https://rfienchinois64k.ice.infomaniak.ch//rfienchinois-64.mp3" },
    { name: "中文新闻循环台", region: "world", url: "https://replaynewszh.ice.infomaniak.ch/replaynewszh-128.mp3" },
    { name: "华语古典音乐", region: "world", url: "https://radio.chinesemusicworld.com/chinesemusic.mp3" }
];

var COCKPIT_RADIO_FM_REGIONS = [
    { key: "all", label: "全部" },
    { key: "gd", label: "广东" },
    { key: "cn", label: "全国" },
    { key: "hmt", label: "港澳台" },
    { key: "world", label: "海外" }
];

var COCKPIT_RADIO_REGIONS = [
    { key: "all", label: "全部" },
    { key: "asia", label: "亚洲" },
    { key: "europe", label: "欧洲" },
    { key: "na", label: "北美" },
    { key: "mideast", label: "中东" },
    { key: "oceania", label: "大洋洲" }
];

var COCKPIT_RADIO_AIRPORTS = [
    { icao: "VHHH", region: "asia", name: "香港赤鱲角", feeds: [
        { label: "连听 App/Dep/Dir/Zone(进近·离场·区调)", url: "https://s1-fmt2.liveatc.net/vhhh5" }
    ]},
    { icao: "WSSS", region: "asia", name: "新加坡樟宜", feeds: [
        { label: "连听 Del/Gnd/App/Radar(放行·地面·进近·雷达)", url: "https://s1-bos.liveatc.net/wsss3" }
    ]}
];

class CockpitRadioPanel extends TemplateElement {
    constructor() {
        super();
        this.currentTab = "fm";
        this.currentRegion = "all";
        this.currentLabel = "";
        this.ws = null;
        this.loaded = false;
    }

    connectedCallback() {
        super.connectedCallback();
        if (this.loaded) return;
        this.loaded = true;

        this.listEl = this.querySelector("#crList");
        this.regionBar = this.querySelector("#crRegions");
        this.npText = this.querySelector("#crNowPlaying");
        this.connEl = this.querySelector("#crConn");
        this.tabFM = this.querySelector("#tabFM");
        this.tabATC = this.querySelector("#tabATC");
        this.volSlider = this.querySelector("#crVolume");
        this.btnStop = this.querySelector("#btnStop");

        this.tabFM.addEventListener("click", () => { this.showTab("fm"); });
        this.tabATC.addEventListener("click", () => { this.showTab("atc"); });
        this.volSlider.addEventListener("input", () => { this.sendVol(this.volSlider.value); });
        this.btnStop.addEventListener("click", () => { this.sendStop(); });

        this.connectServer();
        this.showTab("fm");
    }

    connectServer() {
        try {
            this.ws = new WebSocket("ws://127.0.0.1:8765");
        } catch (e) {
            this.scheduleReconnect();
            return;
        }
        this.ws.onopen = () => {
            if (this.connEl) {
                this.connEl.textContent = "服务已连接";
                this.connEl.style.color = "#7fdd7f";
            }
        };
        this.ws.onclose = () => { this.scheduleReconnect(); };
        this.ws.onerror = () => { /* onclose 接管 */ };
    }

    scheduleReconnect() {
        if (this.connEl) {
            this.connEl.textContent = "服务断开，重连中...";
            this.connEl.style.color = "#ff9d6e";
        }
        setTimeout(() => {
            if (!this.ws || this.ws.readyState === 3) this.connectServer();
        }, 3000);
    }

    send(cmd, extra) {
        if (this.ws && this.ws.readyState === 1) {
            const msg = Object.assign({ role: "panel", cmd: cmd }, extra);
            this.ws.send(JSON.stringify(msg));
            return true;
        }
        if (this.npText) this.npText.textContent = "服务未连接（请先启动 server.py）";
        return false;
    }

    showTab(which) {
        this.currentTab = which;
        if (which === "atc") {
            this.tabATC.classList.add("cr-tab-active");
            this.tabFM.classList.remove("cr-tab-active");
        } else {
            this.tabFM.classList.add("cr-tab-active");
            this.tabATC.classList.remove("cr-tab-active");
        }
        // ATC 不分洲，只有 FM 需要地区筛选栏
        this.regionBar.style.display = (which === "atc") ? "none" : "";
        this.renderRegions();
        this.renderList();
    }

    renderRegions() {
        if (this.currentTab === "atc") { this.regionBar.innerHTML = ""; return; }
        this.regionBar.innerHTML = "";
        const list = COCKPIT_RADIO_FM_REGIONS;
        for (let i = 0; i < list.length; i++) {
            const r = list[i];
            const b = document.createElement("div");
            b.className = "cr-region" + (r.key === this.currentRegion ? " cr-region-active" : "");
            b.textContent = r.label;
            b.addEventListener("click", () => {
                this.currentRegion = r.key;
                this.renderRegions();
                this.renderList();
            });
            this.regionBar.appendChild(b);
        }
    }

    renderList() {
        this.listEl.innerHTML = "";
        if (this.currentTab === "atc") {
            // ATC 不分洲：每个机场一个标题块（显机场名），下面平铺该机场的语音
            for (let i = 0; i < COCKPIT_RADIO_AIRPORTS.length; i++) {
                const ap = COCKPIT_RADIO_AIRPORTS[i];
                const g = document.createElement("div");
                g.className = "cr-group";
                const t = document.createElement("div");
                t.className = "cr-group-title";
                t.textContent = ap.name + "  " + ap.icao;
                g.appendChild(t);
                for (let j = 0; j < ap.feeds.length; j++) {
                    const f = ap.feeds[j];
                    if (!f.url) continue;
                    const item = document.createElement("div");
                    item.className = "cr-item cr-item-live";
                    item.style.cursor = "pointer";
                    item.textContent = "▶ " + f.label;
                    item.addEventListener("click", () => {
                        this.playUrl(f.url, ap.icao + " · " + f.label);
                        this.markActive(item);
                    });
                    g.appendChild(item);
                }
                if (g.children.length > 1) this.listEl.appendChild(g);
            }
        } else {
            const g = document.createElement("div");
            g.className = "cr-group";
            for (let i = 0; i < COCKPIT_RADIO_STATIONS.length; i++) {
                const s = COCKPIT_RADIO_STATIONS[i];
                if (this.currentRegion !== "all" && s.region !== this.currentRegion) continue;
                const item = document.createElement("div");
                item.className = "cr-item";
                item.textContent = s.name;
                item.addEventListener("click", () => {
                    this.playUrl(s.url, s.name);
                    this.markActive(item);
                });
                g.appendChild(item);
            }
            this.listEl.appendChild(g);
        }
    }

    markActive(item) {
        const items = this.listEl.querySelectorAll(".cr-item");
        for (let i = 0; i < items.length; i++) items[i].classList.remove("cr-active");
        item.classList.add("cr-active");
    }

    playUrl(url, name) {
        this.currentLabel = name;
        if (this.send("play", { url: url, name: name })) {
            this.npText.textContent = "正在播放：" + name;
        }
    }

    sendVol(v) {
        this.send("volume", { v: parseInt(v, 10) });
    }

    sendStop() {
        this.currentLabel = "";
        this.npText.textContent = "未播放";
        this.send("stop");
        const items = this.listEl.querySelectorAll(".cr-item");
        for (let i = 0; i < items.length; i++) items[i].classList.remove("cr-active");
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        if (this.ws) {
            try { this.ws.close(); } catch (e) {}
            this.ws = null;
        }
    }
}

window.customElements.define("ingamepanel-custom", CockpitRadioPanel);
checkAutoload();
