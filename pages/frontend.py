import streamlit as st
from backend.core import (
    chatbot, save_message, load_conversation, DB_PATH,
    retrieve_user_threads, add_thread, update_thread_name
)
from langchain_core.messages import HumanMessage, AIMessage
import uuid

# ---------------- Helpers ----------------
def generate_thread_id():
    return str(uuid.uuid4())

def reset_session(username):
    """Initialize session for logged-in user"""
    st.session_state['username'] = username
    st.session_state['authenticated'] = True

    # Load all threads from DB
    threads = retrieve_user_threads(username)
    st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads} if threads else {}

    # Load last thread or create new
    if threads:
        last_thread = threads[-1]["thread_id"]
        st.session_state['thread_id'] = last_thread
        st.session_state['message_history'] = load_conversation(last_thread)
        st.session_state['new_chat'] = False
    else:
        new_id = generate_thread_id()
        st.session_state['thread_id'] = new_id
        st.session_state['message_history'] = []
        st.session_state['new_chat'] = True

# ---------------- Session Initialization ----------------
for key in ["authenticated", "username", "thread_id", "message_history", "new_chat", "chat_threads"]:
    if key not in st.session_state:
        if key == "thread_id":
            st.session_state[key] = generate_thread_id()
        elif key == "message_history":
            st.session_state[key] = []
        elif key == "new_chat":
            st.session_state[key] = True
        elif key == "chat_threads":
            st.session_state[key] = {}
        else:
            st.session_state[key] = False if key=="authenticated" else ""

# ---------------- LOGIN CHECK ----------------
if not st.session_state.get('authenticated', False):
    import Login
    st.stop()

# Ensure all threads are loaded
threads = retrieve_user_threads(st.session_state['username'])
st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads} if threads else {}

# ---------------- SIDEBAR ----------------
st.markdown(
    "<h1 style='text-align: center;'>LangGraph Chatbot</h1>",
    unsafe_allow_html=True
)

st.sidebar.title(st.session_state['username'])

# Logout
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("Login.py")

# New Chat button
if st.sidebar.button("New Chat"):
    new_id = generate_thread_id()
    st.session_state['thread_id'] = new_id
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True
    st.rerun()  # 🔑 force UI refresh to show clean chat

# My Conversations
st.sidebar.header("My Conversations")
for thread_id, name in reversed(list(st.session_state['chat_threads'].items())):
    display_name = name if name else "Untitled Chat"
    if st.sidebar.button(display_name, key=f"btn_thread_{thread_id}"):
        st.session_state['thread_id'] = thread_id
        st.session_state['message_history'] = load_conversation(thread_id)
        st.session_state['new_chat'] = False
        st.rerun()  # 🔑 reload chat window with selected history

# ---------------- CHAT WINDOW ----------------
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# User input
user_input = st.chat_input("Type here...")
if user_input:
    # On first message of new chat, set thread name & save to DB
    if st.session_state['new_chat']:
        thread_name = user_input[:30]  # first 30 chars as title
        add_thread(st.session_state['thread_id'], thread_name, st.session_state['username'])
        st.session_state['chat_threads'][st.session_state['thread_id']] = thread_name
        st.session_state['new_chat'] = False

    # Append user message
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    save_message(st.session_state['thread_id'], 'user', user_input)
    with st.chat_message('user'):
        st.markdown(user_input)

    # Prepare history for LLM
    history = [
        HumanMessage(content=m['content']) if m['role']=='user' else AIMessage(content=m['content'])
        for m in st.session_state['message_history']
    ]

    # Generate assistant response
    response_text = ""
    with st.chat_message('assistant'):
        response_box = st.empty()
        CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
        for message_chunk, _ in chatbot.stream({'messages': history}, config=CONFIG, stream_mode='messages'):
            response_text += message_chunk.content
            response_box.markdown(response_text)

    st.session_state['message_history'].append({'role': 'assistant', 'content': response_text})
    save_message(st.session_state['thread_id'], 'assistant', response_text)
