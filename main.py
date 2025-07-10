# ────────────────────────────────────────────────────────────────
#  날씨 비교 앱 – 날짜 선택(캘린더) 버전
#  ▸ 기본값: 어제
#  ▸ 원하는 날짜 선택 후 모든 지표·그래프 갱신
# ────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# ────────────── 1. 페이지 설정 ──────────────
st.set_page_config(page_title="선택 날짜 vs 역대 기온",
                   page_icon="📈", layout="centered")
st.title("📈 선택한 날은 얼마나 더웠을까?")

# ────────────── 2. CSV 로드 함수 ──────────────
def load_temperature_csv(src, skiprows: int = 7) -> pd.DataFrame:
    """CP949 → UTF-8-SIG 순으로 시도해 CSV를 읽어 DataFrame 반환"""
    for enc in ("cp949", "utf-8-sig"):
        try:
            df = pd.read_csv(src, encoding=enc, skiprows=skiprows)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("지원되지 않는 인코딩입니다.")

    if "날짜" not in df.columns:
        raise ValueError("'날짜' 열이 없습니다.")

    df["날짜"] = pd.to_datetime(df["날짜"].astype(str).str.strip(),
                               format="%Y-%m-%d")
    return df

# ────────────── 3. 파일 업로드 / 기본 파일 ──────────────
uploaded_file = st.file_uploader(
    "CSV 파일을 업로드하세요 (CP949 또는 UTF-8, 7행 설명 포함)", type="csv"
)

if uploaded_file is None:
    default = next((f for f in os.listdir(".")
                    if f.startswith("ta") and f.endswith(".csv")), None)
    if default:
        uploaded_file = default
        st.info(f"기본 파일 **{default}** 을(를) 사용합니다.")
    else:
        st.warning("CSV를 업로드하거나 'ta*.csv' 파일을 폴더에 두세요.")
        st.stop()

try:
    df = load_temperature_csv(uploaded_file)
except Exception as e:
    st.error(f"CSV 로드 오류: {e}")
    st.stop()

# ────────────── 4. 날짜 선택 위젯 ──────────────
min_d, max_d = df["날짜"].dt.date.min(), df["날짜"].dt.date.max()
yesterday = datetime.date.today() - datetime.timedelta(days=1)
default_date = yesterday if (min_d <= yesterday <= max_d) else max_d

selected_date = st.date_input(
    "분석할 날짜를 선택하세요",
    value=default_date,
    min_value=min_d,
    max_value=max_d
)
selected_dt = pd.to_datetime(selected_date)
st.subheader(f"🔍 분석 대상 날짜: {selected_date:%Y-%m-%d}")

df_sel = df[df["날짜"] == selected_dt]
if df_sel.empty:
    st.warning("선택한 날짜의 데이터가 없습니다.")
    st.stop()

# ────────────── 5. 연도 범위 선택 ──────────────
ymin, ymax = int(df["날짜"].dt.year.min()), int(df["날짜"].dt.year.max())
sel_years = st.slider("비교할 연도 범위", ymin, ymax, (ymin, ymax))

same_day_df = df[
    (df["날짜"].dt.strftime("%m-%d") == selected_date.strftime("%m-%d")) &
    (df["날짜"].dt.year.between(*sel_years))
]

# ────────────── 6. 최고·평균·최저 랭킹 계산 ──────────────
high_sel = df_sel["최고기온(℃)"].iloc[0]
avg_sel  = df_sel["평균기온(℃)"].iloc[0]
low_sel  = df_sel["최저기온(℃)"].iloc[0]

rank_high_df = same_day_df.sort_values("최고기온(℃)", ascending=False).reset_index(drop=True)
rank_avg_df  = same_day_df.sort_values("평균기온(℃)", ascending=False).reset_index(drop=True)
rank_low_df  = same_day_df.sort_values("최저기온(℃)").reset_index(drop=True)

rank_high = rank_high_df[rank_high_df["날짜"] == selected_dt].index[0] + 1
rank_avg  = rank_avg_df [rank_avg_df ["날짜"] == selected_dt].index[0] + 1
rank_low  = rank_low_df [rank_low_df ["날짜"] == selected_dt].index[0] + 1

pct_high = 100 * (rank_high - 1) / len(rank_high_df)
pct_avg  = 100 * (rank_avg  - 1) / len(rank_avg_df)
pct_low  = 100 * (rank_low  - 1) / len(rank_low_df)

rec_high = rank_high_df.iloc[0]
rec_avg  = rank_avg_df.iloc[0]
rec_low  = rank_low_df.iloc[0]

# ────────────── 7. 역대 기록 표시 ──────────────
st.markdown("### 🏆 역대 기록")
st.write(f"📈 **역대 최고**: {rec_high['최고기온(℃)']}℃ "
         f"({rec_high['날짜'].date()}) → 선택일보다 "
         f"{rec_high['최고기온(℃)'] - high_sel:+.1f}℃")

st.write(f"🌡️ **역대 평균**: {rec_avg['평균기온(℃)']}℃ "
         f"({rec_avg['날짜'].date()}) → 선택일보다 "
         f"{rec_avg['평균기온(℃)'] - avg_sel:+.1f}℃")

st.write(f"❄️ **역대 최저**: {rec_low['최저기온(℃)']}℃ "
         f"({rec_low['날짜'].date()}) → 선택일보다 "
         f"{rec_low['최저기온(℃)'] - low_sel:+.1f}℃")

# ────────────── 8. metric 카드 ──────────────
c1, c2, c3 = st.columns(3)

c1.metric(
    "🌡️ 선택일 최고기온",
    f"{high_sel:.1f}℃",
    f"상위 {pct_high:.1f}%({len(rank_high_df)}일 중 {rank_high}위)"
)

c2.metric(
    "🌡️ 선택일 평균기온",
    f"{avg_sel:.1f}℃",
    f"상위 {pct_avg:.1f}%({len(rank_avg_df)}일 중 {rank_avg}위)"
)

c3.metric(
    "🌙 선택일 최저기온",
    f"{low_sel:.1f}℃",
    f"상위 {pct_low:.1f}%({len(rank_low_df)}일 중 {rank_low}위)"
)

# ────────────── 9. Top5 표 & 추이 그래프 ──────────────
st.markdown("---")
st.subheader("🔥 가장 더웠던 날 Top 5 (동일 날짜)")
st.dataframe(rank_high_df.head(5).reset_index(drop=True))
fig_high = px.line(rank_high_df.sort_values("날짜"),
                   x="날짜", y="최고기온(℃)",
                   title=f"역대 {selected_date:%m월 %d일} 최고기온 추이")
fig_high.add_scatter(x=[selected_dt], y=[high_sel], mode="markers+text",
                     text=["선택일"], name="선택일",
                     marker=dict(size=12, color="red"),
                     textposition="top center")
st.plotly_chart(fig_high, use_container_width=True)

st.markdown("---")
st.subheader("❄️ 가장 추웠던 날 Top 5 (동일 날짜)")
st.dataframe(rank_low_df.head(5).reset_index(drop=True))
fig_low = px.line(rank_low_df.sort_values("날짜"),
                  x="날짜", y="최저기온(℃)",
                  title=f"역대 {selected_date:%m월 %d일} 최저기온 추이")
fig_low.add_scatter(x=[selected_dt], y=[low_sel], mode="markers+text",
                    text=["선택일"], name="선택일",
                    marker=dict(size=12, color="blue"),
                    textposition="top center")
st.plotly_chart(fig_low, use_container_width=True)

# ────────────── 10. 최근 N일 vs 역대 동일 기간 ──────────────
st.markdown("---")
st.subheader("📅 최근 기간 평균 기온 분석")

day_range = st.slider("비교할 최근 일 수", 3, 30, 14)
start_day = selected_dt - pd.Timedelta(days=day_range)
recent_df = df[(df["날짜"] >= start_day) & (df["날짜"] < selected_dt)]

avg_high = recent_df["최고기온(℃)"].mean()
avg_low  = recent_df["최저기온(℃)"].mean()
avg_mean = recent_df["평균기온(℃)"].mean()

# (1) MM-DD 목록
period_days = [(selected_date - datetime.timedelta(days=i)).strftime("%m-%d")
               for i in range(1, day_range + 1)]

# (2) 연도별 N일 평균
period_df = df[df["날짜"].dt.strftime("%m-%d").isin(period_days)]
yearly_avg = (period_df
              .groupby(period_df["날짜"].dt.year)
              .agg(최고평균=("최고기온(℃)", "mean"),
                   최저평균=("최저기온(℃)", "mean"),
                   평균평균=("평균기온(℃)", "mean"))
              .reset_index())

# (3) 백분위·순위
all_years_mean = yearly_avg["평균평균"]
pct_mean  = 100 * (all_years_mean < avg_mean).sum() / len(all_years_mean)
rank_mean = (all_years_mean > avg_mean).sum() + 1

st.write(f"최근 {day_range}일 평균 (최고/평균/최저): "
         f"**{avg_high:.2f} / {avg_mean:.2f} / {avg_low:.2f}℃**")
st.write(f"역대 동기간 평균 : "
         f"**{yearly_avg['최고평균'].mean():.2f} / "
         f"{yearly_avg['평균평균'].mean():.2f} / "
         f"{yearly_avg['최저평균'].mean():.2f}℃**")
st.info(f"📈 최근 {day_range}일 평균기온은 역대 동일 기간 중 "
        f"상위 **{100-pct_mean:.1f}%** "
        f"(전체 {len(all_years_mean)}개 기간 중 {rank_mean}위)")

# ─── 10-A. 최근 vs 역대 일자별 꺾은선 ───
recent_plot = (recent_df[["날짜", "최고기온(℃)", "최저기온(℃)"]]
               .sort_values("날짜")
               .reset_index(drop=True))
recent_plot["날짜_str"] = recent_plot["날짜"].dt.strftime("%Y-%m-%d")
hist_daily = (period_df
              .groupby(period_df["날짜"].dt.strftime("%m-%d"))
              .agg(역대최고=("최고기온(℃)", "mean"),
                   역대최저=("최저기온(℃)", "mean")))
recent_plot["역대최고"] = recent_plot["날짜"].dt.strftime("%m-%d").map(hist_daily["역대최고"])
recent_plot["역대최저"] = recent_plot["날짜"].dt.strftime("%m-%d").map(hist_daily["역대최저"])

long_df = pd.melt(recent_plot,
                  id_vars="날짜_str",
                  value_vars=["최고기온(℃)", "역대최고",
                              "최저기온(℃)", "역대최저"],
                  var_name="구분", value_name="기온(℃)")

fig_cmp = px.line(long_df, x="날짜_str", y="기온(℃)",
                  color="구분", markers=True,
                  title=f"최근 {day_range}일 실제 vs 역대 평균 (최고·최저)",
                  labels={"날짜_str": "날짜"})
fig_cmp.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_cmp, use_container_width=True)

# ────────────── 11. 최고 vs 최저 스캐터 ──────────────
st.markdown("---")
st.subheader("📍 최고기온 vs 최저기온 분포 (동일 날짜)")

scatter_df = same_day_df.copy()
scatter_df["날짜_str"] = scatter_df["날짜"].dt.strftime("%Y-%m-%d")
scatter_df["선택일"] = scatter_df["날짜"] == selected_dt

fig_scatter = px.scatter(scatter_df,
                         x="최고기온(℃)", y="최저기온(℃)",
                         color="선택일", hover_name="날짜_str",
                         title="역대 최고-최저 분포",
                         labels={"선택일": "선택일 여부"})
st.plotly_chart(fig_scatter, use_container_width=True)
