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
    html, body, [data-testid="stAppViewContainer"], .main {
        overflow: hidden !important;
        margin: 0px !important;
        padding: 0px !important;
    }
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
    # 쿼리 매개변수에서 startLevel 추출하여 시뮬레이터 내 let startLevelParam 변수와 결합
    start_level = query_params.get("startLevel", "null")
    html = html.replace("let startLevelParam = null;", f"let startLevelParam = {start_level};")
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
    html = html.replace('href="sim_v8.html?startLevel=1"', 'href="/?page=sim&startLevel=1"')
    html = html.replace('href="sim_v8.html?startLevel=2"', 'href="/?page=sim&startLevel=2"')
    html = html.replace('href="sim_v8.html?startLevel=3"', 'href="/?page=sim&startLevel=3"')
    html = html.replace('href="sim_v8.html"', 'href="/?page=sim"')
    html = html.replace('href="index.html"', 'href="/"')

import html as pyhtml

# 아이프레임 내부 스크롤 및 앵커 링크 작동이 가능하도록 콤팩트한 높이로 설정
frame_height = 850

escaped_html = pyhtml.escape(html)
iframe_html = f'<iframe srcdoc="{escaped_html}" width="100%" height="{frame_height}" frameborder="0" sandbox="allow-scripts allow-same-origin allow-top-navigation allow-top-navigation-by-user-activation allow-forms allow-popups"></iframe>'
st.markdown(iframe_html, unsafe_allow_html=True)

