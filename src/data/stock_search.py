"""股票搜索 — 内建热门股票库 + 实时搜索

支持三大市场：US / HK / A股
搜索逻辑：symbol 前缀匹配 > name 子串匹配，不区分大小写
"""

# ──────────────────────────────────────────────────────────────
# 内建热门股票库（高频搜索的基础数据）
# ──────────────────────────────────────────────────────────────

_US_STOCKS = [
    # 科技
    ("AAPL",  "Apple"),
    ("MSFT",  "Microsoft"),
    ("GOOGL", "Alphabet (Google)"),
    ("GOOG",  "Alphabet C"),
    ("AMZN",  "Amazon"),
    ("META",  "Meta Platforms"),
    ("NVDA",  "NVIDIA"),
    ("TSLA",  "Tesla"),
    ("NFLX",  "Netflix"),
    ("ORCL",  "Oracle"),
    ("ADBE",  "Adobe"),
    ("CRM",   "Salesforce"),
    ("INTC",  "Intel"),
    ("AMD",   "AMD"),
    ("AVGO",  "Broadcom"),
    ("QCOM",  "Qualcomm"),
    ("TXN",   "Texas Instruments"),
    ("MU",    "Micron Technology"),
    ("AMAT",  "Applied Materials"),
    ("LRCX",  "Lam Research"),
    ("KLAC",  "KLA Corporation"),
    ("ASML",  "ASML Holding"),
    ("TSM",   "TSMC"),
    ("SHOP",  "Shopify"),
    ("SNOW",  "Snowflake"),
    ("PLTR",  "Palantir"),
    ("UBER",  "Uber"),
    ("LYFT",  "Lyft"),
    ("ABNB",  "Airbnb"),
    ("DASH",  "DoorDash"),
    # 消费
    ("KO",    "Coca-Cola"),
    ("PEP",   "PepsiCo"),
    ("MCD",   "McDonald's"),
    ("SBUX",  "Starbucks"),
    ("NKE",   "Nike"),
    ("DIS",   "Disney"),
    ("WMT",   "Walmart"),
    ("COST",  "Costco"),
    ("TGT",   "Target"),
    ("HD",    "Home Depot"),
    ("LOW",   "Lowe's"),
    ("AMGN",  "Amgen"),
    # 金融
    ("JPM",   "JPMorgan Chase"),
    ("BAC",   "Bank of America"),
    ("WFC",   "Wells Fargo"),
    ("GS",    "Goldman Sachs"),
    ("MS",    "Morgan Stanley"),
    ("BRK-B", "Berkshire Hathaway B"),
    ("V",     "Visa"),
    ("MA",    "Mastercard"),
    ("AXP",   "American Express"),
    ("BLK",   "BlackRock"),
    ("SPGI",  "S&P Global"),
    # 医疗
    ("JNJ",   "Johnson & Johnson"),
    ("UNH",   "UnitedHealth"),
    ("PFE",   "Pfizer"),
    ("LLY",   "Eli Lilly"),
    ("ABBV",  "AbbVie"),
    ("MRK",   "Merck"),
    ("TMO",   "Thermo Fisher"),
    ("ABT",   "Abbott Laboratories"),
    # 能源/工业
    ("XOM",   "ExxonMobil"),
    ("CVX",   "Chevron"),
    ("NEE",   "NextEra Energy"),
    ("CAT",   "Caterpillar"),
    ("DE",    "Deere & Company"),
    ("GE",    "GE Aerospace"),
    ("BA",    "Boeing"),
    ("RTX",   "RTX Corporation"),
    # 中概股
    ("BABA",  "Alibaba"),
    ("PDD",   "Pinduoduo (Temu)"),
    ("JD",    "JD.com"),
    ("BIDU",  "Baidu"),
    ("NIO",   "NIO"),
    ("XPEV",  "XPeng"),
    ("LI",    "Li Auto"),
    ("NTES",  "NetEase"),
    ("TME",   "Tencent Music"),
    ("BILI",  "Bilibili"),
]

_HK_STOCKS = [
    # 科技/互联网
    ("0700.HK",  "腾讯控股 Tencent"),
    ("9988.HK",  "阿里巴巴 Alibaba HK"),
    ("9618.HK",  "京东 JD.com HK"),
    ("3690.HK",  "美团 Meituan"),
    ("9999.HK",  "网易 NetEase HK"),
    ("1024.HK",  "快手 Kuaishou"),
    ("2382.HK",  "舜宇光学 Sunny Optical"),
    ("0981.HK",  "中芯国际 SMIC"),
    # 金融
    ("0005.HK",  "汇丰控股 HSBC"),
    ("0939.HK",  "建设银行 CCB"),
    ("1398.HK",  "工商银行 ICBC"),
    ("0941.HK",  "中国移动 China Mobile"),
    ("3988.HK",  "中国银行 BOC"),
    ("0388.HK",  "香港交易所 HKEX"),
    ("2318.HK",  "中国平安 Ping An"),
    ("0011.HK",  "恒生银行 Hang Seng"),
    # 消费/医疗
    ("2269.HK",  "药明生物 WuXi Bio"),
    ("1177.HK",  "中国生物制药"),
    ("0291.HK",  "华润啤酒 CR Beer"),
    ("0175.HK",  "吉利汽车 Geely"),
    ("2020.HK",  "安踏体育 ANTA Sports"),
    ("6690.HK",  "海尔智家 Haier Smart"),
    # 地产/能源
    ("0016.HK",  "新鸿基 Sun Hung Kai"),
    ("0001.HK",  "长和 CK Hutchison"),
    ("0857.HK",  "中国石油 PetroChina"),
    ("0883.HK",  "中国海洋石油 CNOOC"),
    ("1211.HK",  "比亚迪 BYD HK"),
    ("0992.HK",  "联想集团 Lenovo"),
    ("3968.HK",  "招商银行 CMB HK"),
    ("0168.HK",  "青岛啤酒 Tsingtao HK"),
]

_A_STOCKS = [
    # 白酒/消费
    ("sh600519", "贵州茅台"),
    ("sz000858", "五粮液"),
    ("sh600887", "伊利股份"),
    ("sz000333", "美的集团"),
    ("sz000651", "格力电器"),
    ("sh600690", "海尔智家A"),
    ("sh603288", "海天味业"),
    ("sz002304", "洋河股份"),
    ("sh601888", "中国中免"),
    # 医药
    ("sh600276", "恒瑞医药"),
    ("sz300015", "爱尔眼科"),
    ("sz300760", "迈瑞医疗"),
    ("sh688599", "天准科技"),
    ("sz000538", "云南白药"),
    # 科技
    ("sh600036", "招商银行"),
    ("sz000001", "平安银行"),
    ("sh601318", "中国平安"),
    ("sz002415", "海康威视"),
    ("sh603259", "药明康德"),
    ("sz002594", "比亚迪"),
    ("sh688036", "传音控股"),
    ("sh600941", "中国移动A"),
    # 银行/金融
    ("sh601939", "建设银行A"),
    ("sh601398", "工商银行A"),
    ("sh601288", "农业银行"),
    ("sh600016", "民生银行"),
    ("sh601166", "兴业银行"),
    ("sh601328", "交通银行"),
    # 能源/工业
    ("sh600028", "中国石化"),
    ("sh601857", "中国石油A"),
    ("sh600900", "长江电力"),
    ("sh601985", "中国核电"),
    ("sh600309", "万华化学"),
    ("sz000625", "长安汽车"),
    ("sh600177", "雅戈尔"),
    # 新能源
    ("sz300750", "宁德时代"),
    ("sh601012", "隆基绿能"),
    ("sz002129", "中环股份"),
    # AI算力/大模型（十五五主线）
    ("sh688256", "寒武纪"),
    ("sh603019", "中科曙光"),
    ("sz002230", "科大讯飞"),
    ("sh688561", "奇安信"),
    # 机器人/高端装备（十五五主线）
    ("sz300124", "汇川技术"),
    ("sz002747", "埃斯顿"),
    ("sh688507", "复旦微电"),
    ("sh601882", "海天精工"),
    # 半导体/国产替代（十五五主线）
    ("sh688981", "中芯国际"),
    ("sz002371", "北方华创"),
    ("sh603986", "兆易创新"),
    ("sh688012", "中微公司"),
    # 生物医药/创新药（十五五主线）
    ("sh688235", "百济神州"),
    ("sh600763", "通策医疗"),
    ("sh688389", "普源精电"),
    # 低空经济/新质生产力（十五五主线）
    ("sz000768", "中航西飞"),
    ("sh601668", "中国建筑"),
    ("sh688008", "澜起科技"),
]


def search_stocks(query: str, market: str = "all", limit: int = 10) -> list[dict]:
    """搜索股票，返回 [{'symbol': ..., 'name': ..., 'market': ...}, ...]

    Args:
        query: 搜索关键词（股票代码或名称，不区分大小写）
        market: 'all' | 'us' | 'hk' | 'a_share'
        limit: 最多返回多少条
    """
    if not query or len(query.strip()) < 1:
        return []

    q = query.strip().upper()
    q_lower = query.strip().lower()

    candidates = []
    if market in ("all", "us"):
        for sym, name in _US_STOCKS:
            candidates.append({"symbol": sym, "name": name, "market": "us"})
    if market in ("all", "hk"):
        for sym, name in _HK_STOCKS:
            candidates.append({"symbol": sym, "name": name, "market": "hk"})
    if market in ("all", "a_share"):
        for sym, name in _A_STOCKS:
            candidates.append({"symbol": sym, "name": name, "market": "a_share"})

    # Scoring: symbol prefix match scores higher than name substring match
    results = []
    for c in candidates:
        sym_upper = c["symbol"].upper().replace(".HK", "").replace("SH", "").replace("SZ", "")
        name_lower = c["name"].lower()
        score = 0
        if c["symbol"].upper().startswith(q):
            score = 100
        elif sym_upper.startswith(q):
            score = 90
        elif q in c["symbol"].upper():
            score = 70
        elif q_lower in name_lower:
            score = 50
        if score > 0:
            results.append((score, c))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def get_popular_stocks(market: str = "us", limit: int = 20) -> list[dict]:
    """返回某市场的热门股票列表（用于初始化展示）"""
    mapping = {"us": _US_STOCKS, "hk": _HK_STOCKS, "a_share": _A_STOCKS}
    stocks = mapping.get(market, _US_STOCKS)
    return [{"symbol": s, "name": n, "market": market} for s, n in stocks[:limit]]
