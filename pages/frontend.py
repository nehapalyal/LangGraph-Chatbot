import streamlit as st
from backend import (
    chatbot, save_message, load_conversation, DB_PATH,
    retrieve_user_threads
)
from langchain_core.messages import HumanMessage, AIMessage
import uuid, sqlite3

# ---------------- Helpers ----------------
def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True

def reset_session(username):
    st.session_state['username'] = username
    st.session_state['authenticated'] = True
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True
    threads = retrieve_user_threads(username)
    st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads} if threads else {}

def add_thread(thread_id, name, username):
    st.session_state['chat_threads'][thread_id] = name
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO threads (thread_id, name, username) VALUES (?, ?, ?)",
            (thread_id, name, username)
        )
        conn.commit()

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
if not st.session_state["authenticated"]:
    import Login  # or your login UI function
    st.stop()  # stop so chatbot UI doesn’t load

# ---------------- LOAD USER THREADS ----------------
# Add your snippet here
threads = retrieve_user_threads(st.session_state['username'])
if threads:
    # Set the first thread as active
    st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads}
    st.session_state['thread_id'] = threads[0]["thread_id"]
    st.session_state['message_history'] = load_conversation(st.session_state['thread_id'])
    st.session_state['new_chat'] = False
else:
    # No threads, start a new one
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True


# ---------------- CHATBOT UI ----------------
st.sidebar.title(f"Langgraph Chatbot - {st.session_state.get('username','User')}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("/Users/nehapalyal/Desktop/Langgraph chatbot/Login.py")  # Safe to use here after clearing session

if st.sidebar.button("New Chat"):
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True


# Load threads for sidebar
st.sidebar.header("My Conversations")
for thread_id, name in reversed(list(st.session_state['chat_threads'].items())):
    if st.sidebar.button(name, key=f"btn_thread_{thread_id}"):
        st.session_state['thread_id'] = thread_id
        st.session_state['message_history'] = load_conversation(thread_id)
        st.session_state['new_chat'] = False


# Display chat history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# User input
user_input = st.chat_input("Type here...")
if user_input:
    if st.session_state['new_chat']:
        add_thread(st.session_state['thread_id'], user_input[:30], st.session_state['username'])
        st.session_state['new_chat'] = False

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
