import streamlit as st
from backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage
import uuid, sqlite3

# ---------------- Authentication Check ----------------
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ Please login first.")
    st.switch_page("login.py")

# ---------------- Chat Helpers ----------------
def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['message_history'] = []
    st.session_state['new_chat'] = True

def add_thread(thread_id, name):
    st.session_state['chat_threads'][thread_id] = name
    with sqlite3.connect('langgraphChatbot.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO threads (thread_id, name) VALUES (?, ?)", (thread_id, name))
        conn.commit()

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = state.values.get('messages', []) if state else []
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({'role': 'user', 'content': msg.content})
        elif isinstance(msg, AIMessage):
            result.append({'role': 'assistant', 'content': msg.content})
    return result

# ---------------- Session State ----------------
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    threads = retrieve_all_threads()
    st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads} if threads else {}

if 'new_chat' not in st.session_state:
    st.session_state['new_chat'] = True

# ---------------- Sidebar ----------------
st.sidebar.title(f"Langgraph Chatbot - {st.session_state['username']}")

if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.switch_page("login.py")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")
for thread_id, name in reversed(list(st.session_state['chat_threads'].items())):
    if st.sidebar.button(name, key=f"btn-{thread_id}"):
        st.session_state['thread_id'] = thread_id
        st.session_state['message_history'] = load_conversation(thread_id)
        st.session_state['new_chat'] = False

# ---------------- Chat History ----------------
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# ---------------- User Input ----------------
user_input = st.chat_input("Type here...")
if user_input:
    if st.session_state['new_chat']:
        add_thread(st.session_state['thread_id'], user_input[:30])
        st.session_state['new_chat'] = False

    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    response_text = ""
    with st.chat_message('assistant'):
        response_box = st.empty()
        for message_chunk, _ in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config=CONFIG,
            stream_mode='messages'
        ):
            response_text += message_chunk.content
            response_box.markdown(response_text)

    st.session_state['message_history'].append({'role': 'assistant', 'content': response_text})
