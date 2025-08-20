import sqlite3
import hashlib
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

DB_PATH = "langgraphChatbot.db"

# ---------------- Database ----------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # Threads table with username column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                name TEXT,
                username TEXT NOT NULL,
                FOREIGN KEY(username) REFERENCES users(username)
            )
        """)
        conn.commit()

# with sqlite3.connect(DB_PATH) as conn:
#     cursor = conn.cursor()
#     cursor.execute("DROP TABLE IF EXISTS threads")
#     conn.commit()

# init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username: str, password: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)",
            (username.strip(), hash_password(password.strip()))
        )
        conn.commit()

def validate_user(username: str, password: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username.strip(),))
        row = cursor.fetchone()
        return row is not None and row[0] == hash_password(password.strip())

# ---------------- Chatbot ----------------
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash')

class ChatState(dict):
    messages: list[BaseMessage]

def chat_node(state: ChatState):
    messages = state.get('messages', [])
    response = llm.invoke(messages)
    return {'messages': [response]}

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

graph = StateGraph(ChatState)
graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)
chatbot = graph.compile(checkpointer=checkpointer)

# ---------------- Threads ----------------
def retrieve_all_threads():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, name FROM threads")
        rows = cursor.fetchall()
        return [{"thread_id": r[0], "name": r[1]} for r in rows]

def retrieve_user_threads(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, name FROM threads WHERE username=?", (username,))
        rows = cursor.fetchall()
        return [{"thread_id": r[0], "name": r[1]} for r in rows]


def update_thread_name(thread_id: str, new_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE threads SET name=? WHERE thread_id=?", (new_name, thread_id))
        conn.commit()

# ---------------- Messages ----------------
def save_message(thread_id, role, content):
    """Persist messages in LangGraph state"""
    state_snapshot = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = getattr(state_snapshot, 'values', {}).get('messages', []) if state_snapshot else []

    if role == 'user':
        messages.append(HumanMessage(content=content))
    else:
        messages.append(AIMessage(content=content))

    chatbot.update_state(
        values={'messages': messages},
        config={'configurable': {'thread_id': thread_id}}
    )

def load_conversation(thread_id):
    state_snapshot = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    messages = getattr(state_snapshot, 'values', {}).get('messages', []) if state_snapshot else []

    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({'role': 'user', 'content': msg.content})
        elif isinstance(msg, AIMessage):
            result.append({'role': 'assistant', 'content': msg.content})
    return result
