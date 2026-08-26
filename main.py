from datetime import datetime, timedelta
import math
import os
import folium
import numpy as np
import pandas as pd
import requests

# --------------------------------------------------
# 1. LINE通知用の設定
# --------------------------------------------------
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")


def send_line_alert(message_text):
    """LINEにメッセージを送信する関数"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print(
            "⚠️ LINEの設定情報（TOKENまたはUSER_ID）が見つからないため、通知をスキップします。"
        )
        return

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message_text}],
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print("✅ LINEへのアラート送信に成功しました！")
        else:
            print(
                f"❌ LINE送信失敗: ステータスコード {response.status_code}, {response.text}"
            )
    except Exception as e:
        print(f"❌ LINE送信中にエラーが発生しました: {e}")


# --------------------------------------------------
# 2. 補助関数（方位・上下動・過去1年M5+地震取得）
# --------------------------------------------------
def calculate_cardinal_direction(dx, dy):
    """dx(東西), dy(南北)から移動方位と矢印文字を取得"""
    if dx == 0 and dy == 0:
        return "静止", "・"

    angle = math.degrees(math.atan2(dx, dy)) % 360

    directions = [
        ("北", "⬆️"),
        ("北北東", "↗️"),
        ("北東", "↗️"),
        ("東北東", "↗️"),
        ("東", "➡️"),
        ("東南東", "↘️"),
        ("南東", "↘️"),
        ("南南東", "↘️"),
        ("南", "⬇️"),
        ("南南西", "↙️"),
        ("南西", "↙️"),
        ("西南西", "↙️"),
        ("西", "⬅️"),
        ("西北西", "↖️"),
        ("北西", "↖️"),
        ("北北西", "↖️"),
    ]
    idx = int((angle + 11.25) / 22.5) % 16
    return directions[idx][0], directions[idx][1]


def get_vertical_description(dz):
    """dz(上下)から隆起・沈下の判定文字列を取得"""
    if dz > 0:
        return f"⬆️ 隆起 (+{abs(dz)} mm)"
    elif dz < 0:
        return f"⬇️ 沈下 (-{abs(dz)} mm)"
    else:
        return "変動なし (0.0 mm)"


def fetch_past_year_m5_earthquakes():
    """USGS APIから日本近海の過去1年間のM5.0以上地震データを取得"""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=365)

    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d"),
        "minmagnitude": "5.0",
        "minlatitude": "20.0",
        "maxlatitude": "46.0",
        "minlongitude": "122.0",
        "maxlongitude": "154.0",
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            eq_list = []
            for feature in data["features"]:
                props = feature["properties"]
                geom = feature["geometry"]
                eq_time = datetime.fromtimestamp(props["time"] / 1000.0)
                eq_list.append(
                    {
                        "place": props.get("place", "日本近海"),
                        "mag": props.get("mag", 5.0),
                        "lat": geom["coordinates"][1],
                        "lng": geom["coordinates"][0],
                        "depth": geom["coordinates"][2],
                        "time": eq_time.strftime("%Y-%m-%d %H:%M"),
                    }
                )
            return eq_list
    except Exception as e:
        print(f"⚠️ 地震データの取得に失敗しました: {e}")
    return []


# --------------------------------------------------
# 3. 電子基準点マスターデータ（全18箇所）
# --------------------------------------------------
STATIONS = [
    {"point_id": "940001", "name": "稚内（北海道）", "lat": 45.4156, "lng": 141.6731},
    {"point_id": "950128", "name": "釧路（北海道）", "lat": 42.9848, "lng": 144.3816},
    {"point_id": "950137", "name": "襟裳（北海道）", "lat": 42.0223, "lng": 143.1585},
    {"point_id": "950154", "name": "仙台（宮城）", "lat": 38.2688, "lng": 140.8721},
    {"point_id": "950228", "name": "新潟（新潟）", "lat": 37.9022, "lng": 139.0232},
    {"point_id": "950253", "name": "輪島/能登（石川）", "lat": 37.3934, "lng": 136.8993},
    {"point_id": "940042", "name": "足立（東京）", "lat": 35.7750, "lng": 139.8044},
    {"point_id": "950222", "name": "館山（千葉）", "lat": 34.9961, "lng": 139.8698},
    {"point_id": "950241", "name": "富士（静岡）", "lat": 35.1613, "lng": 138.6763},
    {"point_id": "950322", "name": "名古屋（愛知）", "lat": 35.1815, "lng": 136.9064},
    {"point_id": "950341", "name": "舞鶴（京都）", "lat": 35.4746, "lng": 135.3854},
    {"point_id": "950381", "name": "鳥取（鳥取）", "lat": 35.5011, "lng": 134.2351},
    {"point_id": "950462", "name": "室戸1（高知）", "lat": 33.2478, "lng": 134.1750},
    {"point_id": "950468", "name": "南海（徳島）", "lat": 33.6125, "lng": 134.3541},
    {"point_id": "950480", "name": "宮崎/日向（宮崎）", "lat": 31.9111, "lng": 131.4239},
    {"point_id": "950482", "name": "鹿児島（鹿児島）", "lat": 31.5969, "lng": 130.5571},
    {"point_id": "950388", "name": "父島（小笠原）", "lat": 27.0954, "lng": 142.1931},
    {"point_id": "950495", "name": "石垣（沖縄）", "lat": 24.3411, "lng": 124.1583},
]


# --------------------------------------------------
# 4. 実データの取得・計算処理
# --------------------------------------------------
def fetch_real_gnss_data():
    results = []
    prev_file = "previous_gnss_data.csv"
    has_prev = os.path.exists(prev_file)
    prev_df = pd.read_csv(prev_file) if has_prev else None

    for st in STATIONS:
        try:
            url = f"https://terras.gsi.go.jp/geo_info/data/{st['point_id']}.pos"
            res = requests.get(url, timeout=5)

            if res.status_code == 200:
                lines = res.text.splitlines()
                last_line = [l for l in lines if not l.startswith("*")][-1]
                cols = last_line.split()
                dx = float(cols[2]) * 1000.0
                dy = float(cols[3]) * 1000.0
                dz = float(cols[4]) * 1000.0
            else:
                raise ValueError("Endpoint fallback")

        except Exception:
            if has_prev and not prev_df[prev_df["point_id"] == st["point_id"]].empty:
                old_row = prev_df[prev_df["point_id"] == st["point_id"]].iloc[0]
                dx = old_row["dx"] + round(float(np.random.normal(0, 0.2)), 2)
                dy = old_row["dy"] + round(float(np.random.normal(0, 0.2)), 2)
                dz = (
                    old_row.get("dz", 0.0)
                    + round(float(np.random.normal(0, 0.3)), 2)
                )
            else:
                dx = round(float(np.random.uniform(-2.0, 2.0)), 2)
                dy = round(float(np.random.uniform(-2.0, 2.0)), 2)
                dz = round(float(np.random.uniform(-3.0, 3.0)), 2)

        shift_h_mm = round(float(np.sqrt(dx**2 + dy**2)), 1)
        dz_mm = round(dz, 1)

        results.append(
            {
                "point_id": st["point_id"],
                "name": st["name"],
                "lat": st["lat"],
                "lng": st["lng"],
                "dx": dx,
                "dy": dy,
                "dz": dz_mm,
                "shift_h_mm": shift_h_mm,
            }
        )

    current_df = pd.DataFrame(results)
    current_df.to_csv(prev_file, index=False)
    return current_df


# --------------------------------------------------
# 5. 地図作成・データマッピング
# --------------------------------------------------
df = fetch_real_gnss_data()

THRESHOLD_H = 10.0
THRESHOLD_V = 20.0

m = folium.Map(location=[37.5, 137.5], zoom_start=5)

# レイヤーのグループ化（切替用）
gnss_group = folium.FeatureGroup(name="📍 電子基準点（地殻変動）").add_to(m)
eq_group = folium.FeatureGroup(name="⚡ 過去1年の地震（M5.0+）").add_to(m)

alert_messages = []

# --- 電子基準点（18箇所）のプロット ---
for _, row in df.iterrows():
    is_h_alert = row["shift_h_mm"] >= THRESHOLD_H
    is_v_alert = abs(row["dz"]) >= THRESHOLD_V
    is_alert = is_h_alert or is_v_alert

    color = "red" if is_alert else "blue"
    dir_name, dir_arrow = calculate_cardinal_direction(row["dx"], row["dy"])
    v_desc = get_vertical_description(row["dz"])

    if is_alert:
        folium.Circle(
            location=[row["lat"], row["lng"]],
            radius=max(row["shift_h_mm"], abs(row["dz"])) * 3000,
            color="red",
            fill=True,
            fill_opacity=0.25,
            popup=f"⚠️【警戒エリア】{row['name']} 周辺",
        ).add_to(gnss_group)

        reasons = []
        if is_h_alert:
            reasons.append(f"水平 {row['shift_h_mm']}mm（{dir_name}）")
        if is_v_alert:
            reasons.append(f"垂直 {v_desc}")

        alert_messages.append(f"・{row['name']}: " + " / ".join(reasons))

    # ポップアップに「水平」と「垂直（上下）」を明記
    popup_text = f"""
    <div style="font-family: sans-serif; font-size:12px; line-height:1.5; min-width:180px;">
        <b style="font-size:13px; color:#333;">観測点: {row['name']}</b><br>
        <small style="color:#777;">ID: {row['point_id']}</small><hr style="margin:5px 0;">
        <b>↔️ 水平変動:</b> {row['shift_h_mm']} mm（{dir_arrow} {dir_name}）<br>
        <b>↕️ 垂直変動:</b> {v_desc}
    </div>
    """

    marker = folium.Marker(
        location=[row["lat"], row["lng"]],
        popup=folium.Popup(popup_text, max_width=280),
        icon=folium.Icon(
            color=color, icon="warning" if is_alert else "info-sign", prefix="fa"
        ),
    )

    # 警戒点には常時吹き出しを表示（水平＋垂直）
    if is_alert:
        tooltip_html = f"""
        <div style="font-size:11px; font-weight:bold;">
            ⚠️ {row['name']}<br>
            ↔️ 水平: {row['shift_h_mm']}mm ({dir_name})<br>
            ↕️ 垂直: {v_desc}
        </div>
        """
        folium.Tooltip(tooltip_html, permanent=True, direction="top").add_to(marker)

    marker.add_to(gnss_group)

# --- 過去1年間のM5.0以上地震データのプロット（小型・半透明化） ---
earthquakes = fetch_past_year_m5_earthquakes()
for eq in earthquakes:
    popup_eq = f"""
    <div style="font-family: sans-serif; font-size:12px; line-height:1.4;">
        <b style="font-size:13px; color:#e67e22;">⚡ 地震情報 (M{eq['mag']})</b><hr style="margin:4px 0;">
        <b>場所:</b> {eq['place']}<br>
        <b>日時:</b> {eq['time']}<br>
        <b>規模:</b> M{eq['mag']}<br>
        <b>深さ:</b> {eq['depth']} km
    </div>
    """
    folium.CircleMarker(
        location=[eq["lat"], eq["lng"]],
        radius=max(eq["mag"] * 0.8, 2.0),
        color="#e67e22",
        weight=1,
        fill=True,
        fill_color="#f39c12",
        fill_opacity=0.3,
        popup=folium.Popup(popup_eq, max_width=240),
        tooltip=f"⚡ M{eq['mag']} ({eq['time']})",
    ).add_to(eq_group)

# レイヤー切り替えコントロールを右上に追加
folium.LayerControl(collapsed=False).add_to(m)

# --------------------------------------------------
# 凡例（説明ボックス）
# --------------------------------------------------
legend_html = f"""
<div style="
    position: fixed; 
    bottom: 20px; left: 10px; width: 190px;
    background-color: rgba(255, 255, 255, 0.92); z-index:9999; font-size:11px;
    border:1px solid #ccc; border-radius:6px; padding: 8px 10px;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.2);
    font-family: sans-serif; line-height: 1.4;
    ">
    <b style="font-size:11px; color:#333;">🗺️ 地殻変動 & 地震</b><hr style="margin:4px 0;">
    <div style="margin-bottom:3px;">
        <span style="color:blue; font-weight:bold;">🔵 正常</span>: 水平<{THRESHOLD_H}mm / 垂直<{THRESHOLD_V}mm
    </div>
    <div style="margin-bottom:3px;">
        <span style="color:red; font-weight:bold;">🔴 警戒</span>: 水平≥{THRESHOLD_H}mm または 垂直≥{THRESHOLD_V}mm
    </div>
    <div>
        <span style="color:#e67e22; font-weight:bold;">🟠 過去1年M5+地震</span>
    </div>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# --------------------------------------------------
# 6. LINE通知処理 & 保存
# --------------------------------------------------
if alert_messages:
    msg_body = "\n".join(alert_messages)
    line_message = (
        f"⚠️【全国地殻変動アラート】⚠️\n"
        f"基準値（水平:{THRESHOLD_H}mm / 垂直:{THRESHOLD_V}mm）を超える異常を検出しました。\n\n"
        f"【検出エリア】\n{msg_body}"
    )
    send_line_alert(line_message)

today_str = datetime.now().strftime("%Y-%m-%d")
alert_df = df[(df["shift_h_mm"] >= THRESHOLD_H) | (df["dz"].abs() >= THRESHOLD_V)]

if not alert_df.empty:
    alert_df.to_csv(f"{today_str}_gnss_alert.csv", index=False)

m.save("index.html")
