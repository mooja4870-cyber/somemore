import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="SOMEMORE - 노후 자산 시뮬레이터",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit UI 크롬 전체 숨김 CSS 인젝션
st.markdown("""
    <style>
    /* Streamlit 기본 UI 숨김 */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}

    /* 스크롤바 제거 */
    html, body {
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 100% !important;
    }

    /* Streamlit 컨테이너 여백 제거 */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"],
    .main, .block-container,
    section.main > div {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }

    /* components.html 이 생성하는 iframe 풀스크린 */
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        border: none !important;
        z-index: 9999 !important;
        display: block !important;
    }
    </style>
""", unsafe_allow_html=True)

# 쿼리 매개변수를 이용해 페이지 결정 (기본값: home)
query_params = st.query_params
page = query_params.get("page", "home")

if page == "sim":
    # 시뮬레이터 로드
    with open("sim_v8.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    # 쿼리 매개변수에서 startLevel 추출하여 시뮬레이터 내 let startLevelParam 변수와 결합
    start_level = query_params.get("startLevel", "null")
    html_content = html_content.replace("let startLevelParam = null;", f"let startLevelParam = {start_level};")
    # 시뮬레이터 내에서 홈으로 가는 링크가 있을 경우에 대비해 라우팅 경로 보정
    html_content = html_content.replace('href="index.html"', 'href="/"')
else:
    # 홈(랜딩 페이지) 로드
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    with open("index.css", "r", encoding="utf-8") as f:
        css = f.read()

    # index.html 내의 외부 스타일시트 링크를 인라인 스타일로 치환
    html_content = html_content.replace('<link rel="stylesheet" href="index.css">', f'<style>{css}</style>')
    # 3단계 카드 및 시작 버튼 링크를 Streamlit 쿼리 파라미터 링크로 치환
    html_content = html_content.replace('href="sim_v8.html?startLevel=1"', 'href="/?page=sim&startLevel=1"')
    html_content = html_content.replace('href="sim_v8.html?startLevel=2"', 'href="/?page=sim&startLevel=2"')
    html_content = html_content.replace('href="sim_v8.html?startLevel=3"', 'href="/?page=sim&startLevel=3"')
    html_content = html_content.replace('href="sim_v8.html"', 'href="/?page=sim"')
    html_content = html_content.replace('href="index.html"', 'href="/"')

# ✅ st.markdown + srcdoc 방식 대신 components.html 직접 주입
# → HTML 이스케이프 없이 브라우저가 바로 렌더링 (깨짐 완전 방지)
components.html(html_content, height=900, scrolling=True)
