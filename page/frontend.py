import streamlit as st
from backend.core import chatbot, save_message, load_conversation, DB_PATH, retrieve_user_threads
from langchain_core.messages import HumanMessage, AIMessage
import uuid, sqlite3

# ---------------- Session Helpers ----------------
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
    # Load threads for this specific user
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



# ---------------- Authentication Check ----------------
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("⚠️ Please login first.")
    st.switch_page("login")

# ---------------- Session Initialization ----------------
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    threads = retrieve_user_threads(st.session_state['username'])
    st.session_state['chat_threads'] = {t["thread_id"]: t["name"] for t in threads} if threads else {}

if 'new_chat' not in st.session_state:
    st.session_state['new_chat'] = True

# ---------------- Sidebar ----------------
st.sidebar.title(f"Langgraph Chatbot - {st.session_state.get('username','User')}")

if st.sidebar.button("Logout"):
    # Clear all session state
    st.session_state.clear()
    
    # Optionally, set default authentication values
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""

    # Redirect to login page
    st.session_state["redirect"] = True

# Handle redirection
if st.session_state.get("redirect", False):
    st.session_state["redirect"] = False
    st.query_params(page="login")  # redirect using query param
    st.stop()  # stop the current page


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
        add_thread(st.session_state['thread_id'], user_input[:30], st.session_state['username'])
        st.session_state['new_chat'] = False


    # Append user message to session state and save
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    save_message(st.session_state['thread_id'], 'user', user_input)

    with st.chat_message('user'):
        st.markdown(user_input)

    # Prepare full conversation history for LLM
    history = []
    for msg in st.session_state['message_history']:
        if msg['role'] == 'user':
            history.append(HumanMessage(content=msg['content']))
        else:
            history.append(AIMessage(content=msg['content']))

    # Generate assistant response
    response_text = ""
    with st.chat_message('assistant'):
        response_box = st.empty()
        CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
        for message_chunk, _ in chatbot.stream(
            {'messages': history},  # full conversation
            config=CONFIG,
            stream_mode='messages'
        ):
            response_text += message_chunk.content
            response_box.markdown(response_text)

    # Append assistant response to session state and save
    st.session_state['message_history'].append({'role': 'assistant', 'content': response_text})
    save_message(st.session_state['thread_id'], 'assistant', response_text)
