// ============================================================
// 驾驶舱电台 - 频道清单（想加台/删台改这个文件）
// FM 电台带 region：gd 广东 / cn 全国 / hmt 港澳台 / world 海外
// ATC 机场带 region：asia 亚洲 / europe 欧洲 / na 北美 / oceania 大洋洲 / mideast 中东
// ============================================================

const COCKPIT_RADIO_STATIONS = [
    { name: "广州青少年广播 FM88.0", region: "gd", url: "https://lhttp.qtfm.cn/live/20194/64k.mp3" }, //2026校为20194直连mp3(可响); 旧源 http://live.xmcdn.com/live/259/64.m3u8 已失效
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

const COCKPIT_RADIO_FM_REGIONS = [
    { key: "all", label: "全部" },
    { key: "gd", label: "广东" },
    { key: "cn", label: "全国" },
    { key: "hmt", label: "港澳台" },
    { key: "world", label: "海外" }
];

const COCKPIT_RADIO_REGIONS = [
    { key: "all", label: "全部" },
    { key: "asia", label: "亚洲" },
    { key: "europe", label: "欧洲" },
    { key: "na", label: "北美" },
    { key: "mideast", label: "中东" },
    { key: "oceania", label: "大洋洲" }
];

const COCKPIT_RADIO_AIRPORTS = [
    { icao: "VHHH", region: "asia", name: "香港赤鱲角", feeds: [
        { label: "连听 App/Dep/Dir/Zone(进近·离场·区调) - 已验证实时", url: "https://s1-fmt2.liveatc.net/vhhh5" }
    ]},
    { icao: "WSSS", region: "asia", name: "新加坡樟宜", feeds: [
        { label: "连听 Del/Gnd/App/Radar(放行·地面·进近·雷达)", url: "https://s1-bos.liveatc.net/wsss3" }
    ]},];

function getAtcUrl(mount, icao) {
    return "https://www.liveatc.net/hlisten.php?mount=" + mount + "&icao=" + icao;
}
