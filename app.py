import base64
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ================== 核心安全憑證與連線設定 (直接寫死免設 Secrets) ==================
SPREADSHEET_URL = "https://google.com"
GCP_SERVICE_ACCOUNT_BASE64 = "憑證"  # ⚠️請記得把您的那一長串 Base64 憑證英文字貼進來

# 智產權捍衛：內建絕對時間鎖
EXPIRATION_DATE = "2026-08-19"

# 1. 網頁頂部全寬畫面配置
st.set_page_config(page_title="田中工廠設備報修管理戰情監监控中心", layout="wide")

# 🔍 檢查軟體是否已經過期
current_today = pd.Timestamp.now().strftime("%Y-%m-%d")
if current_today > EXPIRATION_DATE:
    st.error("❌ 【系統授權已過期】")
    st.markdown(f"<h2 style='color:#C0392B;'>本系統一週試用期（截止至 {EXPIRATION_DATE}）已屆滿！</h2>", unsafe_allow_html=True)
    st.markdown("<h3>如需繼續延長使用期限、更新工廠數據或獲取正式版授權，請洽原創開發者：<b style='color:#1E88E5;'>chi</b></h3>", unsafe_allow_html=True)
    st.stop()

# 華麗的前端大標題
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏭 田中工廠設備報修管理 ➔ 數據可視化戰情監控中心</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #757575;'>人員維度與進度狀態 • 智慧圓餅圖長條圖比例呈現版 (雲端免設定直連版)</p>", unsafe_allow_html=True)
st.markdown("---")

# ================== 2. 核心功能：連線 Google 試算表與多行黏合器 ==================
@st.cache_data(ttl=3) # 快取 3 秒
def load_and_stitch_perfect_rows_cloud_final():
    try:
        # 🔓 修正：自動清除 Base64 可能含有的換行或空格
        clean_b64 = GCP_SERVICE_ACCOUNT_BASE64.strip().replace("\n", "").replace(" ", "")
        decoded_creds = base64.b64decode(clean_b64).decode("utf-8")
        creds_dict = json.loads(decoded_creds)
        
        scope = ["https://google.com", "https://googleapis.com"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(credentials)
        
        spreadsheet = gc.open_by_url(SPREADSHEET_URL)
        worksheet = spreadsheet.get_worksheet(0) 
        
        raw_data = worksheet.get_all_values()
        if not raw_data:
            st.error("❌ 雲端 Google 試算表內無任何數據！")
            return pd.DataFrame()
            
        structured_list = []
        current_case = None

        # 🚀 修正：精確掃描試算表的每一列與每一欄
        for row in raw_data:
            if len(row) < 5:
                continue

            col_A = str(row[0]).strip()
            col_B = str(row[1]).strip()
            col_C = str(row[2]).strip()
            col_D = str(row[3]).strip()
            col_E = str(row[4]).strip()
            col_F = str(row[5]).strip() if len(row) > 5 else ""

            # 跳過前 7 列的完全空行與欄位標題
            if "報修日期" in col_A or col_A == "nan" or col_A == "":
                if current_case:
                    if col_B and "類別" not in col_B and col_B != "nan": current_case["設備名稱"] += "\n" + col_B
                    if col_C and col_C != "nan": current_case["故障狀況"] += "\n" + col_C
                    if col_D and col_D != "nan": current_case["附件"] += "\n" + col_D
                    if col_E and col_E != "nan": current_case["目前狀態"] += "\n" + col_E
                    if col_F and col_F != "nan": current_case["維修進度備註"] += "\n" + col_F
                continue

            # 🌟 核心：判定這列是不是「新案件的開頭」
            if col_A.startswith("202") or ("202" in col_A and "/" in col_A):
                if current_case:
                    structured_list.append(current_case)

                current_case = {
                    "報修日期／單號": col_A, 
                    "設備名稱": col_B, 
                    "故障狀況": col_C, 
                    "附件": col_D, 
                    "目前狀態": col_E, 
                    "維修進度備註": col_F
                }
            else:
                if current_case:
                    if col_A and col_A != "nan": current_case["報修日期／單號"] += "\n" + col_A
                    if col_B and "類別" not in col_B and col_B != "nan": current_case["設備名稱"] += "\n" + col_B
                    if col_C and col_C != "nan": current_case["故障狀況"] += "\n" + col_C
                    if col_D and col_D != "nan": current_case["附件"] += "\n" + col_D
                    if col_E and col_E != "nan": current_case["目前狀態"] += "\n" + col_E
                    if col_F and col_F != "nan": current_case["維修進度備註"] += "\n" + col_F

        if current_case:
            structured_list.append(current_case)

        clean_df = pd.DataFrame(structured_list)

        if not clean_df.empty:
            # 💡 智慧提取報修人
            clean_df["報修人"] = clean_df["報修日期／單號"].apply(lambda x: 
                next((l for l in str(x).split("\n") if len(l) >= 2 and len(l) <= 4 and not any(z in l for z in ["R2","希望","預計","202"])), "工廠員工")
            )
            
            # 全局名字掃描
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
                        return f"{int(parts[1]):02d}月"
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
    st.markdown("### 📋 歷史報修詳細清單 (與 Excel 標題 100% 相同對齊版)")
    st.dataframe(filtered_df[["報修日期／單號", "設備名稱", "故障狀況", "附件", "目前狀態", "維修進度備註"]], use_container_width=True, height=500)
else:
    st.warning("⚠️ 數據讀取成功，但清洗過後「無符合判定條件」的案件資料。請確認您的 Google 試算表中 A 欄是否包含標準日期格式 (例如 2026/08/12)。")
