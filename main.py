from datetime import datetime
import folium
import numpy as np
import pandas as pd

gnss_real_data = [
    {
        "point_id": "950241",
        "name": "富士",
        "lat": 35.1613,
        "lng": 138.6763,
        "dx": -8.5,
        "dy": 12.3,
    },
    {
        "point_id": "940042",
        "name": "足立",
        "lat": 35.7750,
        "lng": 139.8044,
        "dx": 1.2,
        "dy": -1.8,
    },
    {
        "point_id": "950462",
        "name": "室戸1",
        "lat": 33.2478,
        "lng": 134.1750,
        "dx": -15.2,
        "dy": 18.1,
    },
    {
        "point_id": "950322",
        "name": "名古屋",
        "lat": 35.1815,
        "lng": 136.9064,
        "dx": -3.1,
        "dy": 2.4,
    },
    {
        "point_id": "940001",
        "name": "稚内",
        "lat": 45.4156,
        "lng": 141.6731,
        "dx": -2.0,
        "dy": -1.5,
    },
    {
        "point_id": "950482",
        "name": "鹿児島",
        "lat": 31.5969,
        "lng": 130.5571,
        "dx": -11.0,
        "dy": -6.2,
    },
]

df = pd.DataFrame(gnss_real_data)
df["shift_mm"] = np.sqrt(df["dx"] ** 2 + df["dy"] ** 2).round(1)
THRESHOLD = 10.0

m = folium.Map(location=[37.5, 137.5], zoom_start=5)

for _, row in df.iterrows():
    is_alert = row["shift_mm"] >= THRESHOLD
    color = "red" if is_alert else "blue"

    if is_alert:
        folium.Circle(
            location=[row["lat"], row["lng"]],
            radius=row["shift_mm"] * 3000,
            color="red",
            fill=True,
            fill_opacity=0.3,
            popup=f"⚠️【警戒エリア】{row['name']} 周辺",
        ).add_to(m)

    popup_text = f"<b>観測点: {row['name']} ({row['point_id']})</b><br>・合計変動量: <b>{row['shift_mm']} mm</b>"
    folium.Marker(
        location=[row["lat"], row["lng"]],
        popup=folium.Popup(popup_text, max_width=250),
        icon=folium.Icon(
            color=color,
            icon="warning" if is_alert else "info-sign",
            prefix="fa",
        ),
    ).add_to(m)

today_str = datetime.now().strftime("%Y-%m-%d")
alert_df = df[df["shift_mm"] >= THRESHOLD]

if not alert_df.empty:
    alert_df.to_csv(f"{today_str}_gnss_alert.csv", index=False)

m.save("index.html")
