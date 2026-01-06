import flet as ft
import httpx
from datetime import datetime, timezone, timedelta

# 設定・定数
AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL_BASE = "https://www.jma.go.jp/bosai/forecast/data/forecast/"
JST = timezone(timedelta(hours=9))


# 天気テキスト
def normalize_weather(text: str) -> str:
    return text.replace("　", " ").replace("時々", "、時々").replace("後", "のち")

# 天気に応じたUI要素の決定
def get_weather_style(text: str):
    if "雪" in text: return "❄️", ft.Colors.CYAN_50, ft.Icons.SNOWING
    if "雷" in text: return "⛈️", ft.Colors.AMBER_50, ft.Icons.THUNDERSTORM
    if "雨" in text: return "🌧️", ft.Colors.BLUE_50, ft.Icons.WATER_DROP
    if "曇" in text or "くもり" in text: return "☁️", ft.Colors.GREY_50, ft.Icons.CLOUD
    if "晴" in text: return "☀️", ft.Colors.ORANGE_50, ft.Icons.SUNNY
    return "🌤️", ft.Colors.WHITE, ft.Icons.WB_SUNNY_OUTLINED

async def main(page: ft.Page):
    page.title = "気象庁高度天気予報アプリ"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#f5f7fa"
    
    # 状態管理用UI
    status_text = ft.Text("地域を選択してください", size=14, color=ft.Colors.GREY_700)
    loading_ring = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)
    weather_display = ft.Column(expand=True, scroll=ft.ScrollMode.ADAPTIVE, spacing=15)

    # 天気取得・表示処理
    async def fetch_weather(e):
        area_code = e.control.data
        area_name = e.control.title.value
        
        # 画面の初期化とステータス更新
        weather_display.controls.clear()
        loading_ring.visible = True
        status_text.value = f"「{area_name}」のデータを取得中..."
        page.update()

        try:
            async with httpx.AsyncClient(verify=False) as client:
                res = await client.get(f"{FORECAST_URL_BASE}{area_code}.json")
                data = res.json()

                # エリア内詳細予報
                report = data[0]
                for area_data in report["timeSeries"][0]["areas"]:
                    sub_area_name = area_data["area"]["name"]
                    weathers = area_data["weathers"]
                    times = report["timeSeries"][0]["timeDefines"]

                    forecast_items = []
                    for i in range(min(3, len(weathers))):
                        w_raw = weathers[i]
                        w_clean = normalize_weather(w_raw)
                        emoji, bg, icon = get_weather_style(w_raw)
                        date_str = datetime.fromisoformat(times[i].replace('Z', '+00:00')).astimezone(JST).strftime('%m/%d')

                        forecast_items.append(
                            ft.Container(
                                content=ft.Row([
                                    ft.Text(emoji, size=30),
                                    ft.Column([
                                        ft.Text(f"{date_str} ({['今日', '明日', '明後日'][i]})", size=12, color=ft.Colors.GREY_600),
                                        ft.Text(w_clean, size=15, weight="bold"),
                                    ], spacing=2, expand=True)
                                ]),
                                padding=12, bgcolor=bg, border_radius=8
                            )
                        )

                    weather_display.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.ListTile(leading=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.BLUE), title=ft.Text(f"{sub_area_name} の予報", weight="bold")),
                                    ft.Column(forecast_items, spacing=5)
                                ], spacing=10),
                                padding=15
                            )
                        )
                    )
                
                status_text.value = f"{area_name} の予報を表示中 (取得完了)"
                status_text.color = ft.Colors.BLUE_700

        except Exception as ex:
            status_text.value = f"エラーが発生しました: {ex}"
            status_text.color = ft.Colors.RED
        
        loading_ring.visible = False
        page.update()

    # 地域リスト構築
    sidebar_content = ft.ListView(expand=True, spacing=0)

    async def load_areas():
        async with httpx.AsyncClient(verify=False) as client:
            res = await client.get(AREA_URL)
            area_data = res.json()
            for c_code, c_info in area_data.get("centers", {}).items():
                tiles = [
                    ft.ListTile(
                        title=ft.Text(area_data["offices"][o_code]["name"], size=13),
                        data=o_code, on_click=fetch_weather
                    ) for o_code in c_info.get("children", []) if o_code in area_data["offices"]
                ]
                sidebar_content.controls.append(ft.ExpansionTile(title=ft.Text(c_info["name"], size=14, weight="bold"), controls=tiles))
        page.update()

    # レイアウト配置
    page.add(
        ft.Row([
            # サイドバー
            ft.Container(
                width=260, bgcolor=ft.Colors.WHITE,
                content=ft.Column([
                    ft.Container(ft.Text("地域一覧", size=18, weight="bold"), padding=20),
                    ft.Divider(height=1),
                    sidebar_content
                ])
            ),
            # メイン画面
            ft.Container(
                expand=True, padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WB_CLOUDY, color=ft.Colors.BLUE_400, size=30),
                        ft.Text("気象庁天気予報", size=24, weight="bold"),
                        ft.VerticalDivider(),
                        loading_ring,
                        status_text
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(),
                    weather_display
                ])
            )
        ], expand=True, spacing=0)
    )

    await load_areas()

ft.app(target=main)