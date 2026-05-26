import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="SOMEMORE - 노후 자산 시뮬레이터",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit의 기본 여백, 메뉴, 푸터 등 레이아웃을 숨기고 아이프레임을 화면에 꽉 채우기 위한 CSS 인젝션
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding: 0px !important;
        margin: 0px !important;
    }
    iframe {
        width: 100vw;
        height: 100vh;
        border: none;
        display: block;
    }
    div[data-testid="stVerticalBlock"] > div {
        padding: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

# 쿼리 매개변수를 이용해 페이지 결정 (기본값: home)
query_params = st.query_params
page = query_params.get("page", "home")

if page == "sim":
    # 시뮬레이터 로드
    with open("sim_v8.html", "r", encoding="utf-8") as f:
        html = f.read()
    # 시뮬레이터 내에서 홈으로 가는 링크가 있을 경우에 대비해 라우팅 경로 보정
    html = html.replace('href="index.html"', 'href="/"')
else:
    # 홈(랜딩 페이지) 로드
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    with open("index.css", "r", encoding="utf-8") as f:
        css = f.read()
    
    # index.html 내의 외부 스타일시트 링크를 인라인 스타일로 치환 (아이프레임 내에서 로드되도록)
    html = html.replace('<link rel="stylesheet" href="index.css">', f'<style>{css}</style>')
    # 3단계 카드 및 시작 버튼 링크를 Streamlit 쿼리 파라미터 링크로 치환
    html = html.replace('href="sim_v8.html"', 'href="/?page=sim"')
    html = html.replace('href="index.html"', 'href="/"')

# 전체 화면 스크롤이 가능하도록 높이를 넉넉히 잡고 HTML 렌더링
# 랜딩 페이지는 2200px, 시뮬레이터는 1400px 수준으로 유동적 설정
frame_height = 2200 if page != "sim" else 1400

components.html(html, height=frame_height, scrolling=True)
