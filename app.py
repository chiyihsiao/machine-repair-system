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
        st.markdown("### 📱 歷史報修詳細清單 (手機響應式垂直卡片優化版)")
        
        # 🌟 核心改裝：不在手機上顯示大表格，而是將每筆資料轉換為「往下生長」的精美卡片
        if not filtered_df.empty:
            for idx, row_data in filtered_df.iterrows():
                # 根據不同狀態給予卡片左側不同的顏色邊框
                status_now = row_data["精確進度狀態"]
                border_color = color_map.get(status_now, "#9E9E9E")
                
                # 美化換行文字，將 \n 換成網頁的 <br> 標籤
                date_box = str(row_data["報修日期／單號"]).replace("\n", "<br>")
                device_box = str(row_data["設備名稱"]).replace("\n", "<br>")
                trouble_box = str(row_data["故障狀況"]).replace("\n", "<br>")
                status_box = str(row_data["目前狀態"]).replace("\n", "<br>")
                memo_box = str(row_data["維修進度備註"]).replace("\n", "<br>") if row_data["維修進度備註"] else "無備註"

                # 建立純 HTML 手機卡片框架，寬度 100% 自動符合不溢出
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
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("目前無符合篩選條件的報修案件。")
            
    else:
        st.warning("⚠️ 數據讀取成功，但清洗過後「無符合判定條件」的案件資料。請確認您的 Google 試算表中 A 欄是否包含標準日期格式 (例如 2026/08/12)。")
