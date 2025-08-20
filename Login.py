import streamlit as st
from backend import validate_user, add_user

st.title("🔑 Login to My Chatbot")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

tab1, tab2 = st.tabs(["Login", "Register"])

# ---------------- Login ----------------
with tab1:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if validate_user(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success("✅ Login successful! Redirecting...")
            st.switch_page("pages/frontend.py")  # <--- redirect to chatbot page
        else:
            st.error("❌ Invalid username or password")

# ---------------- Register ----------------
with tab2:
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    if st.button("Register"):
        if new_user and new_pass:
            add_user(new_user, new_pass)
            st.success("🎉 User registered! Please login.")
        else:
            st.warning("⚠️ Please enter username and password.")