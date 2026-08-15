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
st.markdown("<p style='text-align: center; color: #757575;'>人員維度與進度狀態 • 智慧圓餅圖長條圖比例呈現版 (雲端同步終極安全永久版)</p>", unsafe_allow_html=True)
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
            base64_creds = st.secrets["gcp_service_account_base64"]
            decoded_bytes = base64.b64decode(base64_creds)
            creds_json = decoded_bytes.decode("utf-8")
            creds_dict = json.loads(creds_json)
            
            gc = gspread.service_account_from_dict(creds_dict)
            spreadsheet_url = st.secrets["spreadsheet_url"]
            spreadsheet = gc.open_by_url(spreadsheet_url)
            worksheet = spreadsheet.get_worksheet(0)
            
            # 軌道一 🚀：最穩定的純文字模式，精確撈取所有儲存格文字
            raw_text_data = worksheet.get_all_values()
            if not raw_text_data:
                st.error("❌ 雲端 Google 試算表內無任何數據！")
                return pd.DataFrame()
            
            # 軌道二 🚀：高階向下要求提取底層元數據，用來解鎖一個格子多行、多個超連結
            sheet_data = spreadsheet.fetch_sheet_metadata({"includeGridData": True})
            grid_data = sheet_data["sheets"][0].get("data", [])[0].get("rowData", [])
            # 建立一個地圖，存放每一列 D 欄（附件）精確拆解出的超連結清單
            row_url_map = {}
            for r_idx, row_meta in enumerate(grid_data):
                cells_meta = row_meta.get("values", [])
                if len(cells_meta) > 3: # 有涵蓋到 D 欄 (索引 3)
                    d_cell = cells_meta[3]
                    formatted_val = d_cell.get("formattedValue", "").strip()
                    
                    # 排除沒有照片的 "-" 符號
                    if not formatted_val or formatted_val == "-":
                        continue
                        
                    links_found = []
                    text_runs = d_cell.get("textFormatRuns", [])
                    
                    # ✨【終極多網址解包引擎】：如果一格裡面有換行、多個關鍵字照片連結 (報修圖、完工圖)
                    if text_runs and formatted_val:
                        for i in range(len(text_runs)):
                            start_idx = text_runs[i].get("startIndex", 0)
                            end_idx = text_runs[i+1].get("startIndex", len(formatted_val)) if i+1 < len(text_runs) else len(formatted_val)
                            
                            run_text = formatted_val[start_idx:end_idx].strip()
                            run_format = text_runs[i].get("format", {})
                            run_url = run_format.get("link", {}).get("uri", "")
                            
                            # 嚴格篩選：只有當文字出現「圖」或「照片」關鍵字，且網址存在時才撈取
                            if run_url and any(k in run_text for k in ["圖", "照片", "連結", "報修", "完工"]):
                                links_found.append((run_text, run_url))
                                
                    # 模式 B 退路：若儲存格內是傳統單一標準超連結結構
                    if not links_found:
                        url = d_cell.get("hyperlink", "")
                        if url:
                            label = formatted_val if formatted_val else "照片連結"
                            links_found.append((label, url))
                            
                    if links_found:
                        row_url_map[r_idx] = links_found

            structured_list = []
            current_case = None

            # 🚀 開始進行多行黏合迴圈 (全覆蓋 A 到 G 欄)
            for idx, row in enumerate(raw_text_data):
                if not row or len(row) == 0:
                    continue

                col_A = str(row[0]).strip() if len(row) > 0 else ""  # 報修日期／單號
                col_B = str(row[1]).strip() if len(row) > 1 else ""  # 設備名稱
                col_C = str(row[2]).strip() if len(row) > 2 else ""  # 故障狀況
                col_E = str(row[4]).strip() if len(row) > 4 else ""  # 目前狀態
                col_F = str(row[5]).strip() if len(row) > 5 else ""  # 維修進度備註
                col_G = str(row[6]).strip() if len(row) > 6 else ""  # 處理過程 (G欄)

                if not any([col_A, col_B, col_C, col_E, col_F, col_G]):
                    continue

                if "報修日期" in col_A or "設備名稱" in col_B or "故障狀況" in col_C:
                    continue

                has_urls_list = row_url_map.get(idx, [])

                # 💡 智慧判定新案件條件
                is_new_case = False
                if col_A and (col_A.startswith("202") or ("202" in col_A and "/") in col_A):
                    is_new_case = True
                elif col_B and col_B.lower() != "nan" and any(k in col_B for k in ["機", "區", "門", "模", "線"]):
                    is_new_case = True

                if is_new_case:
                    if current_case:
                        structured_list.append(current_case)
                    
                    current_case = {
                        "報修日期／單號": col_A if col_A.lower() != "nan" else "", 
                        "設備名稱": col_B if col_B.lower() != "nan" else "", 
                        "故障狀況": col_C if col_C.lower() != "nan" else "", 
                        "圖片連結清單": list(has_urls_list),  # 放入挖到的照片連結陣列
                        "currently": col_E if col_E.lower() != "nan" else "",
                        "currently_F": col_F if col_F.lower() != "nan" else "",
                        "目前狀態": col_E if col_E.lower() != "nan" else "", 
                        "維修進度備註": col_F if col_F.lower() != "nan" else "",
                        "後台處理人員欄": col_G if col_G.lower() != "nan" else ""
                    }
                else:
                    # 💡 次行換行黏合資料
                    if current_case:
                        if col_A and col_A.lower() != "nan": current_case["報修日期／單號"] += "\n" + col_A
                        if col_B and "類別" not in col_B and col_B.lower() != "nan": 
                            current_case["設備名稱"] += ("\n" if current_case["設備名稱"] else "") + col_B
                        if col_C and col_C.lower() != "nan": current_case["故障狀況"] += ("\n" if current_case["故障狀況"] else "") + col_C
                        
                        # ✨【照片黏合深層去重】：只黏合真正乾淨的 (名稱, 網址) Tuple 物件，杜絕殘留 HTML
                        if has_urls_list:
                            for url_item in has_urls_list:
                                if isinstance(url_item, (tuple, list)) and len(url_item) == 2:
                                    if url_item not in current_case["圖片連結清單"] and not str(url_item[1]).startswith("<div"):
                                        current_case["圖片連結清單"].append(url_item)
                                        
                        if col_E and col_E.lower() != "nan": 
                            current_case["currently"] = current_case["currently"] + "\n" + col_E
                            current_case["目前狀態"] = current_case["目前狀態"] + "\n" + col_E
                        if col_F and col_F.lower() != "nan": current_case["維修進度備註"] += "\n" + col_F
                        if col_G and col_G.lower() != "nan": current_case["後台處理人員欄"] += "\n" + col_G

            if current_case:
                structured_list.append(current_case)

            clean_df = pd.DataFrame(structured_list)

            # ================== 資料清洗與特徵工程 ==================
            if not clean_df.empty:
                clean_df["報修人"] = clean_df["報修日期／單號"].apply(lambda x: 
                    next((l for l in str(x).split("\n") if len(l) >= 2 and len(l) <= 4 and not any(z in l for z in ["R2","希望","預計","202"])), "工廠員工")
                )
                
                def clean_engineer_name(row_data):
                    g_text = str(row_data.get("後台處理人員欄", "")).strip()
                    e_text = str(row_data.get("currently", "")).strip()
                    f_text = str(row_data.get("currently_F", "")).strip()
                    for t in [g_text, e_text, f_text]:
                        if "蕭志成" in t: return "蕭志成"
                        elif "蕭吉義" in t: return "蕭吉義"
                        elif "葛明輝" in t: return "葛明輝"
                        for l in t.split("\n"):
                            if "承辦" in l: return l.replace("承辦：", "").replace("承辦:", "").strip()
                    return "未指派/待審核"
                    
                clean_df["承辦人"] = clean_df.apply(clean_engineer_name, axis=1)
                
                def split_status_five_layers(status_text):
                    t = str(status_text)
                    if "已完成" in t or "完工" in t: return "已完成"
                    elif "待驗收" in t: return "待主管審核"
                    elif "維修中" in t: return "維修中"
                    elif "待主管審核" in t: return "待主管審核"
                    else: return "設備課待處理"
                    
                clean_df["精確進度狀態"] = clean_df["currently"].apply(split_status_five_layers)

                # ✨【智慧月份提取終極安全版】：精確指定 parts[1] 取出月份數字，絕不 int(list) 導致掛掉
                def extract_month_label(datetime_text):
                    try:
                        first_line = str(datetime_text).split("\n")[0].strip()
                        if "/" in first_line:
                            parts = first_line.split("/")
                            if len(parts) > 1:
                                month_num = int(parts[1])
                                return f"{month_num:02d}月"
                        elif "-" in first_line:
                            parts = first_line.split("-")
                            if len(parts) > 1:
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
                fig_bar = px.bar(bar_data, x="承辦人", y="件數", color="精確進度狀態", barmode="stack", text_auto=True, height=320, template="plotly_white", color_discrete_map=color_map)
                fig_bar.update_layout(xaxis_title="工程師姓名", yaxis_title="總案件數量 (件)", legend_title="案件狀態", bargap=0.45, xaxis={'type': 'category', 'categoryorder': 'total descending'})
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("無數據可顯示長條圖")

        st.markdown("---")
        st.markdown("### 📱 歷史報修詳細清單 (手機響應式垂直卡片 + 雲端照片直顯優化版)")
        
        if not filtered_df.empty:
            for idx, row_data in filtered_df.iterrows():
                status_now = row_data["精確進度狀態"]
                border_color = color_map.get(status_now, "#9E9E9E")
                
                def force_get_text(val, fallback_msg=""):
                    if pd.isna(val) or str(val).strip().lower() == "nan" or str(val).strip() == "":
                        return fallback_msg
                    return str(val).replace("\n", "<br>")

                date_box = force_get_text(row_data.get("報修日期／單號"), "（未填日期）")
                device_box = force_get_text(row_data.get("設備名稱"), "（未填設備）")
                trouble_box = force_get_text(row_data.get("故障狀況"), "（未填狀況）")
                status_box = force_get_text(row_data.get("目前狀態"), "（無狀態描述）")
                memo_box = force_get_text(row_data.get("維修進度備註"), "無備註")
                
                engineer_assigned = str(row_data.get("承辦人", "未指派")).strip()
                
                # 🚀 ✨【超完美雙重過濾牆】：切除被二度黏合污染的原始碼，只渲染乾淨的按鈕
                links_html = ""
                if "圖片連結清單" in row_data and row_data["圖片連結清單"]:
                    try:
                        seen = set()
                        for item in row_data["圖片連結清單"]:
                            if isinstance(item, (tuple, list)) and len(item) == 2:
                                text_label, link_url = item
                                text_label = str(text_label).replace("\n", "").strip()
                                link_url = str(link_url).strip()
                                
                                # 💡 強制攔截：只要網址裡藏有破碎的 <div> 語法，直接攔截不顯示！
                                if link_url and not link_url.startswith("<div") and link_url not in seen:
                                    seen.add(link_url)
                                    links_html += f"""
                                    <div style='margin-top: 8px; background-color: #E3F2FD; padding: 8px; border-radius: 6px; border: 1px solid #BBDEFB; text-align: center; display: inline-block; margin-right: 10px;'>
                                        <a href='{link_url}' target='_blank' style='color: #0D47A1; text-decoration: none; font-size: 13px; font-weight: bold;'>🔗 點擊觀看 [{text_label}] 照片</a>
                                    </div>
                                    """
                    except:
                        pass

                card_html = f"""
                <div style='border-left: 8px solid {border_color}; background-color: #F8F9FA; padding: 15px; border-radius: 5px; margin-bottom: 15px; box-shadow: 1px 1px 5px rgba(0,0,0,0.05);'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                        <span style='font-size: 13px; color: #666;'>📅 {date_box}</span>
                        <span style='background-color: {border_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;'>{status_now}</span>
                    </div>
                    <p style='margin: 8px 0; font-size: 16px; color: #111;'><b>🛠️ 設備名稱：</b><br><span style='color:#0D47A1; font-weight:bold;'>{device_box}</span></p>
                    <p style='margin: 8px 0; font-size: 15px; color: #333;'><b>🚨 故障狀況：</b><br>{trouble_box}</p>
                    <p style='margin: 5px 0; font-size: 14px; color: #2E7D32;'><b>👨‍🔧 負責工程師：</b><br><span style='background-color:#E8F5E9; padding:2px 6px; border-radius:4px; font-weight:bold;'>{engineer_assigned}</span></p>
                    <p style='margin: 5px 0; font-size: 14px; color: #444;'><b>💬 目前進度狀態：</b><br>{status_box}</p>
                    <p style='margin: 5px 0; font-size: 13px; color: #777; background-color: #FFF; padding: 6px; border-radius: 4px; border: 1px dashed #DDD;'><b>📝 維修備註：</b><br>{memo_box}</p>
                    <div style='margin-top: 10px;'>{links_html}</div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("目前無符合篩選條件的報修案件。")
            
    else:
        st.warning("⚠️ 數據讀取成功，但清洗過後「無符合判定條件」的案件資料。請確認您的 Google 試算表中 A 欄是否包含標準日期格式 (例如 2026/08/12)。")
