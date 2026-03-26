"""同行业竞争对手映射表

当分析某只股票时，自动查找 2-3 只最相关的同行竞品，
用于 AI 对比分析，提升分析深度和说服力。
"""

# 格式: symbol → [(peer_symbol, peer_name, peer_market), ...]
_PEERS: dict[str, list[tuple]] = {

    # ── 美股科技 ──────────────────────────────────────────────────────
    "AAPL":  [("MSFT", "Microsoft", "us"), ("GOOGL", "Alphabet", "us"), ("SSNLF", "Samsung", "us")],
    "MSFT":  [("AAPL", "Apple", "us"), ("GOOGL", "Alphabet", "us"), ("ORCL", "Oracle", "us")],
    "GOOGL": [("META", "Meta", "us"), ("MSFT", "Microsoft", "us"), ("SNAP", "Snap", "us")],
    "GOOG":  [("META", "Meta", "us"), ("MSFT", "Microsoft", "us"), ("SNAP", "Snap", "us")],
    "META":  [("GOOGL", "Alphabet", "us"), ("SNAP", "Snap", "us"), ("PINS", "Pinterest", "us")],
    "AMZN":  [("MSFT", "Microsoft", "us"), ("GOOGL", "Alphabet", "us"), ("BABA", "Alibaba", "us")],
    "NVDA":  [("AMD", "AMD", "us"), ("INTC", "Intel", "us"), ("AVGO", "Broadcom", "us")],
    "AMD":   [("NVDA", "NVIDIA", "us"), ("INTC", "Intel", "us"), ("QCOM", "Qualcomm", "us")],
    "INTC":  [("AMD", "AMD", "us"), ("NVDA", "NVIDIA", "us"), ("QCOM", "Qualcomm", "us")],
    "TSLA":  [("NIO", "NIO", "us"), ("GM", "GM", "us"), ("F", "Ford", "us")],
    "NFLX":  [("DIS", "Disney", "us"), ("WBD", "Warner Bros", "us"), ("PARA", "Paramount", "us")],
    "SHOP":  [("AMZN", "Amazon", "us"), ("ETSY", "Etsy", "us"), ("WMT", "Walmart", "us")],

    # ── 美股金融 ──────────────────────────────────────────────────────
    "JPM":   [("BAC", "Bank of America", "us"), ("WFC", "Wells Fargo", "us"), ("GS", "Goldman Sachs", "us")],
    "BAC":   [("JPM", "JPMorgan", "us"), ("WFC", "Wells Fargo", "us"), ("C", "Citigroup", "us")],
    "V":     [("MA", "Mastercard", "us"), ("AXP", "American Express", "us"), ("PYPL", "PayPal", "us")],
    "MA":    [("V", "Visa", "us"), ("AXP", "American Express", "us"), ("PYPL", "PayPal", "us")],
    "BRK-B": [("JPM", "JPMorgan", "us"), ("AIG", "AIG", "us"), ("MKL", "Markel", "us")],

    # ── 美股消费 ──────────────────────────────────────────────────────
    "KO":    [("PEP", "PepsiCo", "us"), ("MNST", "Monster Beverage", "us"), ("STZ", "Constellation", "us")],
    "PEP":   [("KO", "Coca-Cola", "us"), ("MNST", "Monster Beverage", "us"), ("MDLZ", "Mondelez", "us")],
    "MCD":   [("SBUX", "Starbucks", "us"), ("YUM", "Yum Brands", "us"), ("QSR", "Restaurant Brands", "us")],
    "SBUX":  [("MCD", "McDonald's", "us"), ("DNUT", "Krispy Kreme", "us"), ("DNKN", "Dunkin", "us")],
    "NKE":   [("ADDYY", "Adidas", "us"), ("UAA", "Under Armour", "us"), ("LULU", "Lululemon", "us")],
    "WMT":   [("COST", "Costco", "us"), ("TGT", "Target", "us"), ("AMZN", "Amazon", "us")],

    # ── 美股医疗 ──────────────────────────────────────────────────────
    "JNJ":   [("PFE", "Pfizer", "us"), ("ABT", "Abbott", "us"), ("MDT", "Medtronic", "us")],
    "LLY":   [("NVO", "Novo Nordisk", "us"), ("ABBV", "AbbVie", "us"), ("MRK", "Merck", "us")],
    "UNH":   [("CVS", "CVS Health", "us"), ("CI", "Cigna", "us"), ("HUM", "Humana", "us")],

    # ── 中概股 ────────────────────────────────────────────────────────
    "BABA":  [("JD", "JD.com", "us"), ("PDD", "Pinduoduo", "us"), ("0700.HK", "Tencent", "hk")],
    "JD":    [("BABA", "Alibaba", "us"), ("PDD", "Pinduoduo", "us"), ("0700.HK", "Tencent", "hk")],
    "PDD":   [("BABA", "Alibaba", "us"), ("JD", "JD.com", "us"), ("9618.HK", "JD HK", "hk")],
    "BIDU":  [("GOOGL", "Alphabet", "us"), ("0700.HK", "Tencent", "hk"), ("9999.HK", "NetEase", "hk")],
    "NIO":   [("XPEV", "XPeng", "us"), ("LI", "Li Auto", "us"), ("TSLA", "Tesla", "us")],
    "XPEV":  [("NIO", "NIO", "us"), ("LI", "Li Auto", "us"), ("TSLA", "Tesla", "us")],
    "LI":    [("NIO", "NIO", "us"), ("XPEV", "XPeng", "us"), ("TSLA", "Tesla", "us")],

    # ── 港股 ──────────────────────────────────────────────────────────
    "0700.HK": [("9988.HK", "Alibaba HK", "hk"), ("9618.HK", "JD HK", "hk"), ("1024.HK", "Kuaishou", "hk")],
    "9988.HK": [("0700.HK", "Tencent", "hk"), ("9618.HK", "JD HK", "hk"), ("3690.HK", "Meituan", "hk")],
    "3690.HK": [("0700.HK", "Tencent", "hk"), ("9988.HK", "Alibaba HK", "hk"), ("0241.HK", "Alibaba Health", "hk")],
    "9618.HK": [("9988.HK", "Alibaba HK", "hk"), ("0700.HK", "Tencent", "hk"), ("3690.HK", "Meituan", "hk")],
    "0005.HK": [("0939.HK", "CCB", "hk"), ("1398.HK", "ICBC", "hk"), ("3988.HK", "BOC", "hk")],
    "2318.HK": [("0966.HK", "China Taiping", "hk"), ("1336.HK", "NCI", "hk"), ("2328.HK", "PICC", "hk")],
    "1211.HK": [("NIO", "NIO", "us"), ("LI", "Li Auto", "us"), ("0175.HK", "Geely", "hk")],
    "0175.HK": [("1211.HK", "BYD HK", "hk"), ("0489.HK", "Dongfeng", "hk"), ("2238.HK", "GAC", "hk")],
    "2020.HK": [("NKE", "Nike", "us"), ("ADDYY", "Adidas", "us"), ("0551.HK", "Yue Yuen", "hk")],

    # ── A股白酒 ───────────────────────────────────────────────────────
    "sh600519": [("sz000858", "五粮液", "a_share"), ("sz002304", "洋河股份", "a_share"), ("sh600809", "山西汾酒", "a_share")],
    "sz000858": [("sh600519", "贵州茅台", "a_share"), ("sz002304", "洋河股份", "a_share"), ("sh603369", "今世缘", "a_share")],
    "sz002304": [("sh600519", "贵州茅台", "a_share"), ("sz000858", "五粮液", "a_share"), ("sh600809", "山西汾酒", "a_share")],

    # ── A股消费/家电 ─────────────────────────────────────────────────
    "sz000333": [("sz000651", "格力电器", "a_share"), ("sh600690", "海尔智家", "a_share"), ("sz002415", "海康威视", "a_share")],
    "sz000651": [("sz000333", "美的集团", "a_share"), ("sh600690", "海尔智家", "a_share"), ("sh603288", "海天味业", "a_share")],
    "sh600887": [("sz000895", "双汇发展", "a_share"), ("sh603288", "海天味业", "a_share"), ("sh600519", "贵州茅台", "a_share")],

    # ── A股医药 ───────────────────────────────────────────────────────
    "sh600276": [("sz300760", "迈瑞医疗", "a_share"), ("sz300015", "爱尔眼科", "a_share"), ("sh603259", "药明康德", "a_share")],
    "sz300760": [("sh600276", "恒瑞医药", "a_share"), ("sz300015", "爱尔眼科", "a_share"), ("sz002415", "海康威视", "a_share")],

    # ── A股新能源 ─────────────────────────────────────────────────────
    "sz300750": [("sh601012", "隆基绿能", "a_share"), ("sz002129", "中环股份", "a_share"), ("sz002594", "比亚迪", "a_share")],
    "sz002594": [("sz300750", "宁德时代", "a_share"), ("sh601012", "隆基绿能", "a_share"), ("sz000625", "长安汽车", "a_share")],

    # ── A股银行 ───────────────────────────────────────────────────────
    "sh600036": [("sz000001", "平安银行", "a_share"), ("sh601166", "兴业银行", "a_share"), ("sh601328", "交通银行", "a_share")],
    "sz000001": [("sh600036", "招商银行", "a_share"), ("sh601166", "兴业银行", "a_share"), ("sh601998", "中信银行", "a_share")],
}


def get_peers(symbol: str, market: str = "", limit: int = 3) -> list[dict]:
    """返回 symbol 的竞争对手列表

    Returns: [{'symbol': ..., 'name': ..., 'market': ...}, ...]
    """
    key = symbol.upper()
    # Try direct match first
    if key in _PEERS:
        peers = _PEERS[key][:limit]
        return [{"symbol": p[0], "name": p[1], "market": p[2]} for p in peers]

    # Try lower-case A-share (e.g. sh600519)
    key_lower = symbol.lower()
    if key_lower in _PEERS:
        peers = _PEERS[key_lower][:limit]
        return [{"symbol": p[0], "name": p[1], "market": p[2]} for p in peers]

    return []
