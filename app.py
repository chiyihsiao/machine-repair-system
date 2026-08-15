import base64
import json
import re
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread

# 1. 網頁頂部全寬畫面配置
st.set_page_config(page_title="田中工廠設備報修管理戰情監控中心", layout="wide")

# 華麗的前端大標題
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏭 田中工廠設備報修管理 ➔ 數據可視化戰情監控中心</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #757575;'>人員維度與進度狀態 • 智慧圓餅圖長條圖比例呈現版 (雲端同步照片直顯永久版)</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 🔐 密碼保護機制 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.markdown("<h3 style='text-align: center; color: #1E88E5; font-weight: bold;'>🏭 田中工廠報修系統 安全登入</h3>", unsafe_allow_html=True)
    user_password = st.text_input("🔑 請輸入工廠專屬連線密碼", type="password")
    if st.button("確認登入", type="primary", use_container_width=True):
        if user_password == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤，請重新輸入！")
    return False

# 🌟 如果密碼正確，才執行後續所有內容
if check_password():

    # ================== 2. 核心功能：連線 Google 試算表與多行黏合器 ==================
    @st.cache_data(ttl=3) # 快取 3 秒
    def load_and_stitch_perfect_rows_cloud_final():
        try:
            # 🌟 採用憑證解碼機制
            base64_creds = st.secrets["gcp_service_account_base64"]
            decoded_bytes = base64.b64decode(base64_creds)
            creds_json = decoded_bytes.decode("utf-8")
            creds_dict = json.loads(creds_json)
            
            gc = gspread.service_account_from_dict(creds_dict)
            spreadsheet_url = st.secrets["spreadsheet_url"]
            spreadsheet = gc.open_by_url(spreadsheet_url)
            worksheet = spreadsheet.get_worksheet(0) # 預設讀取第一個工作表
            
            # 🚀 終極改裝：使用 FORMULA 模式讀取，才能挖出 =HYPERLINK("網址", "顯示文字") 的內容
            raw_data_formulas = worksheet.get_all_values(value_render_option="FORMULA")
            if not raw_data_formulas:
                st.error("❌ 雲端 Google 試算表內無任何數據！")
                return pd.DataFrame()
                
            structured_list = []
            current_case = None

            # 輔助函式：從公式中精確提取真正的網址
            def extract_url_from_formula(cell_text):
                text_str = str(cell_text).strip()
                if "HYPERLINK" in text_str:
                    urls = re.findall(r'"(https?://[^"]+)"', text_str)
                    if urls:
                        return urls[0]
                return ""

            # 🚀 重新精確讀取所有欄位（包含 D 欄附件）
            for row in raw_data_formulas:
                if len(row) < 5:
                    continue

                col_A = str(row[0]).strip() if len(row) > 0 else ""
                col_B = str(row[1]).strip() if len(row) > 1 else ""
                col_C = str(row[2]).strip() if len(row) > 2 else ""
                col_D_raw = str(row[3]).strip() if len(row) > 3 else "" # 這是未處理的 D 欄公式
                col_E = str(row[4]).strip() if len(row) > 4 else ""
                col_F = str(row[5]).strip() if len(row) > 5 else ""

                # 處理附件欄文字與網址
                img_url = extract_url_from_formula(col_D_raw)

                # 跳過空行與標題列
                if "報修日期" in col_A or col_A == "nan" or col_A == "":
                    if current_case:
                        if col_B and "類別" not in col_B and col_B != "nan": current_case["設備名稱"] += "\n" + col_B
                        if col_C and col_C != "nan": current_case["故障狀況"] += "\n" + col_C
                        if img_url: current_case["圖片連結"] = img_url # 如果多行中有包含網址就保留
                        if col_E and col_E != "nan": current_case["目前狀態"] += "\n" + col_E
                        if col_F and col_F != "nan": current_case["維修進度備註"] += "\n" + col_F
                    continue

                # 判定新案件開頭
                if col_A.startswith("202") or ("202" in col_A and "/" in col_A):
                    if current_case:
                        structured_list.append(current_case)

                    current_case = {
                        "報修日期／單號": col_A, 
                        "設備名稱": col_B, 
                        "故障狀況": col_C, 
                        "圖片連結": img_url, # 新增存放真正的雲端照片網址
                        "目前狀態": col_E, 
                        "維修進度備註": col_F
                    }
                else:
                    if current_case:
                        if col_A and col_A != "nan": current_case["報修日期／單號"] += "\n" + col_A
                        if col_B and "類別" not in col_B and col_B != "nan": current_case["設備名稱"] += "\n" + col_B
                        if col_C and col_C != "nan": current_case["故障狀況"] += "\n" + col_C
                        if img_url: current_case["圖片連結"] = img_url
                        if col_E and col_E != "nan": current_case["currently"] = current_case["目前狀態"] = current_case["目前狀態"] + "\n" + col_E
                        if col_F and col_F != "nan": current_case["維修進度備註"] += "\n" + col_F

            if current_case:
                structured_list.append(current_case)

            clean_df = pd.DataFrame(structured_list)

            if not clean_df.empty:
                # 智慧提取報修人
                clean_df["報修人"] = clean_df["報修日期／單號"].apply(lambda x: 
                    next((l for l in str(x).split("\n") if len(l) >= 2 and len(l) <= 4 and not any(z in l for z in ["R2","希望","預計","202"])), "工廠員工")
                )
                
                # 全局工程師人名純化
                def clean_engineer_name(status_text):
                    t = str(status_text)
                    if "蕭志成" in t: return "蕭志成"
                    elif "蕭吉義" in t: return "蕭吉義"
                    elif "葛明輝" in t: return "葛明輝"
                    
                    for l in t.split("\n"):
                        if "承辦" in l:
                            return l.replace("承辦：", "").replace("承辦:", "").strip()
                    return "未指派/待審核"
                    
                clean_df["承辦人"] = clean_df["目前狀態"].apply(clean_engineer_name)
                
                # 四層進度分類
                def split_status_four_layers(status_text):
                    t = str(status_text)
                    if "已完成" in t or "完工" in t: return "已完成"
                    elif "維修中" in t: return "維修中"
                    elif "待主管審核" in t: return "待主管審核"
                    else: return "設備課待處理"
                    
                clean_df["精確進度狀態"] = clean_df["目前狀態"].apply(split_status_four_layers)

                # 月份安全提取
                def extract_month_label(datetime_text):
                    try:
                        first_line = str(datetime_text).split("\n")[0].strip()
                        if "/" in first_line:
                            parts = first_line.split("/")
                            month_num = int(parts[1])
                            return f"{month_num:02d}月"
                    except:
                        pass
                    return "08月"

                clean_df["報修月份"] = clean_df["報修日期／單號"].apply(extract_month_label)

            return clean_df
        except Exception as e:
            st.error(f"❌ 雲端數據讀取或清洗失敗，原因: {e}")
            return pd.DataFrame()

    df = load_and_stitch_perfect_rows_cloud_final()
    # ================== 3. Streamlit 前端網頁大螢幕呈現 ==================
    if not df.empty:
        total_cases = len(df)
        completed_cases = len(df[df["精確進度狀態"] == "已完成"])
        pending_cases = total_cases - completed_cases

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f"<div style='background-color:#E3F2FD; padding:15px; border-radius:10px; text-align:center;'><h4 style='color:#0D47A1;margin:0;'>📋 總報修件數</h4><h2 style='color:#0D47A1;margin:5px 0;'>{total_cases} 件</h2></div>", unsafe_allow_html=True)
        k2.markdown(f"<div style='background-color:#FFEBEE; padding:15px; border-radius:10px; text-align:center;'><h4 style='color:#B71C1C;margin:0;'>⏳ 處理中／待審核</h4><h2 style='color:#B71C1C;margin:5px 0;'>{pending_cases} 件</h2></div>", unsafe_allow_html=True)
        k3.markdown(f"<div style='background-color:#E8F5E9; padding:15px; border-radius:10px; text-align:center;'><h4 style='color:#1B5E20;margin:0;'>✅ 廠區已完工</h4><h2 style='color:#1B5E20;margin:5px 0;'>{completed_cases} 件</h2></div>", unsafe_allow_html=True)
        
        rate = (completed_cases / total_cases * 100) if total_cases > 0 else 0.0
        k4.markdown(f"<div style='background-color:#FFF3E0; padding:15px; border-radius:10px; text-align:center;'><h4 style='color:#E65100;margin:0;'>📈 完工達成率</h4><h2 style='color:#E65100;margin:5px 0;'>{rate:.1f} %</h2></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔍 智慧人員與時間進度篩選系統")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            available_months = ["全部月份"] + sorted(list(df["報修月份"].unique()))
            selected_month = st.selectbox("📅 按【報修月份】查詢：", available_months)
        with f2:
            selected_user = st.selectbox("👤 按【報修人員姓名】快速篩選：", ["全部報修人"] + sorted(list(df["報修人"].unique())))
        with f3:
            selected_assignee = st.selectbox("👨‍🔧 按【承辦維修人員】快速篩選：", ["全部承辦人"] + sorted(list(df["承辦人"].unique())))
        with f4:
            selected_status = st.selectbox("🚦 按【目前進度狀態】精確篩選：", ["全部狀態", "已完成", "維修中", "待主管審核", "設備課待處理"])

        filtered_df = df.copy()
        if selected_month != "全部月份": filtered_df = filtered_df[filtered_df["報修月份"] == selected_month]
        if selected_user != "全部報修人": filtered_df = filtered_df[filtered_df["報修人"] == selected_user]
        if selected_assignee != "全部承辦人": filtered_df = filtered_df[filtered_df["承辦人"] == selected_assignee]
        if selected_status != "全部狀態": filtered_df = filtered_df[filtered_df["精確進度狀態"] == selected_status]

        st.markdown(f"💡 目前依據選單過濾出：<b style='color:#1E88E5; font-size:18px;'>{len(filtered_df)}</b> 筆符合條件的工廠報修紀錄。", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2 = st.columns(2)
        color_map = {"已完成": "#2ECC71", "維修中": "#3498DB", "待主管審核": "#F39C12", "設備課待處理": "#E74C3C"}
        
        with col1:
            st.write("**🚨 篩選範圍內：全流程維修進度狀態比例 (圓餅圖)**")
            if not filtered_df.empty:
                pie_data = filtered_df["精確進度狀態"].value_counts().reset_index()
                pie_data.columns = ["狀態", "件數"]
                st.plotly_chart(px.pie(pie_data, values="件數", names="狀態", hole=0.4, height=320, color="狀態", color_discrete_map=color_map), use_container_width=True)
            else:
                st.info("無數據可顯示圓餅圖")

        with col2:
            st.write("**👨‍🔧 各工程師承辦案件狀態比例 (強制垂直堆疊長條圖)**")
            if not filtered_df.empty:
                bar_data = filtered_df.groupby(["承辦人", "精確進度狀態"]).size().reset_index(name="件數")
                
                fig_bar = px.bar(
                    bar_data, 
                    x="承辦人", 
                    y="件數", 
                    color="精確進度狀態", 
                    barmode="stack",
                    text_auto=True, 
                    height=320, 
                    template="plotly_white", 
                    color_discrete_map=color_map
                )
                
                fig_bar.update_layout(
                    xaxis_title="工程師姓名",
                    yaxis_title="總案件數量 (件)",
                    legend_title="案件狀態",
                    bargap=0.45,
                    xaxis={'type': 'category', 'categoryorder': 'total descending'}
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("無數據可顯示長條圖")

        st.markdown("---")
        st.markdown("### 📱 歷史報修詳細清單 (手機響應式垂直卡片 + 雲端照片直顯優化版)")
        
        if not filtered_df.empty:
            for idx, row_data in filtered_df.iterrows():
                status_now = row_data["精確進度狀態"]
                border_color = color_map.get(status_now, "#9E9E9E")
                
                date_box = str(row_data["報修日期／單號"]).replace("\n", "<br>")
                device_box = str(row_data["設備名稱"]).replace("\n", "<br>")
                trouble_box = str(row_data["故障狀況"]).replace("\n", "<br>")
                status_box = str(row_data["目前狀態"]).replace("\n", "<br>")
                memo_box = str(row_data["維修進度備註"]).replace("\n", "<br>") if row_data["維修進度備註"] else "無備註"
                
                # 🚀 智慧照片按鈕建構
                photo_html = ""
                if row_data["圖片連結"]:
                    photo_html = f"""
                    <div style='margin-top: 12px; background-color: #E3F2FD; padding: 10px; border-radius: 6px; border: 1px solid #BBDEFB; text-align: center;'>
                        <a href='{row_data["圖片連結"]}' target='_blank' style='color: #0D47A1; text-decoration: none; font-size: 14px; font-weight: bold;'>🖼️ 點擊在新分頁看現場報修/完工圖</a>
                    </div>
                    """

                card_html = f"""
                <div style='
                    border-left: 8px solid {border_color}; 
                    background-color: #F8F9FA; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-bottom: 15px; 
                    box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
                '>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                        <span style='font-size: 13px; color: #666;'>📅 {date_box}</span>
                        <span style='background-color: {border_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;'>{status_now}</span>
                    </div>
                    <p style='margin: 5px 0; font-size: 15px;'><b>🛠️ 設備名稱：</b><br>{device_box}</p>
                    <p style='margin: 5px 0; font-size: 15px;'><b>🚨 故障狀況：</b><br>{trouble_box}</p>
                    <p style='margin: 5px 0; font-size: 14px; color: #444;'><b>👨‍🔧 目前狀態欄：</b><br>{status_box}</p>
                    <p style='margin: 5px 0; font-size: 13px; color: #777; background-color: #FFF; padding: 6px; border-radius: 4px; border: 1px dashed #DDD;'><b>📝 維修備註：</b><br>{memo_box}</p>
                    {photo_html}
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("目前無符合篩選條件的報修案件。")
            
    else:
        st.warning("⚠️ 數據讀取成功，但清洗過後「無符合判定條件」的案件資料。請確認您的 Google 試算表中 A 欄是否包含標準日期格式 (例如 2026/08/12)。")
