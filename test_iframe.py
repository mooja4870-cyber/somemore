import streamlit as st
import html as pyhtml

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
</style>
""", unsafe_allow_html=True)

html = """
<html><body>
<h2>Hello from srcdoc iframe</h2>
<a href="/?page=sim" target="_top">Go to Sim</a>
<script>
    console.log("Script running in srcdoc");
</script>
</body></html>
"""
escaped_html = pyhtml.escape(html)
iframe_html = f'<iframe srcdoc="{escaped_html}" style="width:100vw; height:100vh; border:none;" sandbox="allow-scripts allow-same-origin allow-top-navigation allow-top-navigation-by-user-activation allow-forms allow-popups"></iframe>'
st.markdown(iframe_html, unsafe_allow_html=True)
