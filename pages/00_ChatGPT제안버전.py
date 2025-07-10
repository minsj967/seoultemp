# ────────────────────────────────────────────────────────────────
#  선택 날짜 vs 역대 기온 – 전문가 + 일반인 친화 버전
#  ▸ 사이드바 UI
#  ▸ 평년(1991-2020) Δ, Heat Index, TOP10
# ────────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import datetime as dt
import os, math
import plotly.express as px

# ────────────── 0. 공통 함수 ──────────────
def load_csv(src, skiprows=7):
    for enc in ("cp949", "utf-8-sig"):
        try:
            df = pd.read_csv(src, encoding=enc, skiprows=skiprows)
            break
        except UnicodeDecodeError:
            continue
    else:
        st.error("CSV 인코딩을 확인하세요."); st.stop()

    if "날짜" not in df.columns:
        st.error("'날짜' 열이 없습니다."); st.stop()

    df["날짜"] = pd.to_datetime(df["날짜"].astype(str).str.strip(), format="%Y-%m-%d")
    return df

def heat_index_c(t_c, rh):
    """섭씨·RH(%) → Heat Index(섭씨). 논리적 범위 외에는 원본 반환."""
    t_f = t_c * 9/5 + 32
    if t_f < 80 or rh < 40:
        return t_c
    hi_f = (-42.379 + 2.04901523*t_f + 10.14333127*rh
            - .22475541*t_f*rh - 6.83783e-3*t_f**2
            - 5.481717e-2*rh**2 + 1.22874e-3*t_f**2*rh
            + 8.5282e-4*t_f*rh**2 - 1.99e-6*t_f**2*rh**2)
    return (hi_f - 32) * 5/9

# ────────────── 1. 페이지 ──────────────
st.set_page_config("선택 날짜 vs 역대 기온", "📈", "centered")
st.title("📈 선택 날짜는 평년보다 얼마나 더웠을까?")

# ────────────── 2. 데이터 로드 ──────────────
up = st.file_uploader("CSV 업로드 (or 기본 ta*.csv)", type="csv")
if up is None:
    up = next((f for f in os.listdir(".") if f.startswith("ta") and f.endswith(".csv")), None)
    if up: st.info(f"기본 파일 **{up}** 사용")
    else: st.stop()

df = load_csv(up)

# ────────────── 3. 사이드바 입력 ──────────────
sb = st.sidebar
sb.header("⚙️ 설정")

min_d, max_d = df["날짜"].dt.date.min(), df["날짜"].dt.date.max()
yesterday = dt.date.today() - dt.timedelta(days=1)
default_d = yesterday if min_d <= yesterday <= max_d else max_d

sel_date = sb.date_input("날짜 선택", default_d, min_value=min_d, max_value=max_d)
sel_dt   = pd.to_datetime(sel_date)

ymin, ymax = int(df["날짜"].dt.year.min()), int(df["날짜"].dt.year.max())
year_rng   = sb.slider("비교 연도 범위", ymin, ymax, (ymin, ymax))

day_rng    = sb.slider("최근 N일(평균 비교)", 3, 30, 14)

show_expl  = sb.checkbox("📖 각 섹션 설명 보기", value=True)

rh = sb.slider("체감온도 계산용 습도(%)", 10, 100, 60)

# ────────────── 4. 선택일 존재 확인 ──────────────
df_sel = df[df["날짜"] == sel_dt]
if df_sel.empty():
    st.error("선택한 날짜 데이터가 없습니다."); st.stop()

# ────────────── 5. 동일 MM-DD 데이터, 평년값 ──────────────
mmdd = sel_dt.strftime("%m-%d")
same_day = df[df["날짜"].dt.strftime("%m-%d") == mmdd]
same_day_yr = same_day[same_day["날짜"].dt.year.between(*year_rng)]

# WMO 1991-2020 평년
clim_base = same_day[(same_day["날짜"].dt.year >= 1991) &
                     (same_day["날짜"].dt.year <= 2020)]
if clim_base.empty: clim_base = same_day_yr   # fallback

clim_mean = clim_base[["최고기온(℃)", "평균기온(℃)", "최저기온(℃)"]].mean()

# ────────────── 6. 선택일 값 & Δ ──────────────
high, avg, low = df_sel.iloc[0][["최고기온(℃)", "평균기온(℃)", "최저기온(℃)"]]
Δhigh, Δavg, Δlow = high - clim_mean[0], avg - clim_mean[1], low - clim_mean[2]

# Heat Index
hi_c = heat_index_c(high, rh)

# ────────────── 7. 랭킹 계산 ──────────────
def rank_pct(series, val, ascending=False):
    sorted_s = series.sort_values(ascending=ascending).reset_index(drop=True)
    rank = sorted_s[sorted_s == val].index[0] + 1
    pct  = 100 * (rank - 1) / len(sorted_s)
    return rank, pct, len(sorted_s)

rank_high, pct_high, n_high = rank_pct(same_day_yr["최고기온(℃)"], high, False)
rank_low , pct_low , n_low  = rank_pct(same_day_yr["최저기온(℃)"], low, True)

# ────────────── 8. 카드(모바일→ col 1) ──────────────
cols = st.columns(2 if st.session_state.get("mobile", False) else 3)
cols[0].metric("🌡️ 최고기온",   f"{high:.1f}°C",
               f"Δ {Δhigh:+.1f}°C · 상위 {pct_high:.1f}% ({n_high}일 중 {rank_high}위)")
cols[1].metric("🌡️ 평균기온",   f"{avg:.1f}°C",
               f"Δ {Δavg:+.1f}°C")
if len(cols) > 2:
    cols[2].metric("🌙 최저기온", f"{low:.1f}°C",
                   f"Δ {Δlow:+.1f}°C · 상위 {pct_low:.1f}% ({n_low}일 중 {rank_low}위)")

st.metric("🥵 체감 최고(Heat Index)", f"{hi_c:.1f}°C", f"습도 {rh}% 기준")

# ────────────── 9. TOP10 표 ──────────────
st.markdown("---")
st.subheader("🔥 동일 날짜 TOP 10 최고/최저")
if show_expl:
    st.caption("같은 월·일 기준, 선택 연도 범위에서 상·하위 10위를 보여줍니다.")

c_top, c_low = st.columns(2)
c_top.dataframe(same_day_yr.sort_values("최고기온(℃)", ascending=False)
                .head(10)[["날짜", "최고기온(℃)"]]
                .reset_index(drop=True))
c_low.dataframe(same_day_yr.sort_values("최저기온(℃)").head(10)
                [["날짜", "최저기온(℃)"]]
                .reset_index(drop=True))

# ────────────── 10. 추이 그래프 ──────────────
st.markdown("---")
st.subheader(f"📉 {mmdd} 최고·최저 기온 추이")
if show_expl:
    st.caption("선형 회귀 기울기는 기후 변화 경향성을 의미합니다.")

fig_line = px.scatter(same_day_yr, x="날짜", y="최고기온(℃)",
                      trendline="ols", labels={"최고기온(℃)":"기온(°C)"})
fig_line.add_scatter(x=[sel_dt], y=[high], mode="markers+text",
                     text=["선택일"], name="선택일", marker=dict(size=12, color="red"))
st.plotly_chart(fig_line, use_container_width=True)

# ────────────── 11. 최근 N일 vs 평년 그래프 ──────────────
st.markdown("---")
st.subheader(f"⏳ 최근 {day_rng}일 평균 vs 평년")
if show_expl:
    st.caption("선택일 기준 과거 N일과 1991-2020 평년 평균을 비교합니다.")

start_dt = sel_dt - pd.Timedelta(days=day_rng)
recent_df = df[(df["날짜"] >= start_dt) & (df["날짜"] < sel_dt)]
per_days = [(sel_date - dt.timedelta(days=i)).strftime("%m-%d") for i in range(1, day_rng+1)]
clim_df  = df[df["날짜"].dt.strftime("%m-%d").isin(per_days) &
              (df["날짜"].dt.year.between(1991, 2020))]
clim_mean_line = (clim_df.groupby(clim_df["날짜"].dt.strftime("%m-%d"))
                           ["평균기온(℃)"].mean())

recent_plot = recent_df.sort_values("날짜")[["날짜","평균기온(℃)"]]
recent_plot["평년"] = recent_plot["날짜"].dt.strftime("%m-%d").map(clim_mean_line)

fig_cmp = px.line(recent_plot.melt("날짜", var_name="구분", value_name="평균"),
                  x="날짜", y="평균", color="구분", markers=True,
                  labels={"평균":"평균기온(°C)"})
st.plotly_chart(fig_cmp, use_container_width=True)
