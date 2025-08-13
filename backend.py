from langgraph.graph import StateGraph,START,END,add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash')

class ChatState(TypedDict):
  messages: Annotated[list[BaseMessage],add_messages]

def chat_node(state:ChatState):
  messages = state['messages'] # taking the user input
  response = llm.invoke(messages) # generating the response using the llm
  return {'messages':[response]} # returning the response

checkpointer = InMemorySaver()

graph = StateGraph(ChatState)

graph.add_node('chat_node',chat_node)

graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot = graph.compile(checkpointer=checkpointer)

