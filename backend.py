import sqlite3
import hashlib
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver

load_dotenv()

# ---------------- Database ----------------
DB_PATH = "langgraphChatbot.db"

def init_db():
    """Create required tables"""
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
        # Threads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        conn.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username: str, password: str):
    """Add a new user (hashed password)"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (username, password) VALUES (?, ?)",
            (username.strip(), hash_password(password.strip()))
        )
        conn.commit()

def validate_user(username: str, password: str) -> bool:
    """Check login credentials"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (username.strip(),))
        row = cursor.fetchone()
        if row is None:
            return False
        return row[0] == hash_password(password.strip())

# ---------------- Chatbot ----------------
# Initialize LLM
llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash')

# Define Chat State
class ChatState(dict):
    messages: list[BaseMessage]

def chat_node(state: ChatState):
    messages = state.get('messages', [])
    response = llm.invoke(messages)
    return {'messages': [response]}

# LangGraph setup
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

graph = StateGraph(ChatState)
graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)
chatbot = graph.compile(checkpointer=checkpointer)

# Threads utilities
def retrieve_all_threads():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, name FROM threads")
        rows = cursor.fetchall()
        return [{"thread_id": r[0], "name": r[1]} for r in rows]

def update_thread_name(thread_id: str, new_name: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE threads SET name=? WHERE thread_id=?", (new_name, thread_id))
        conn.commit()
