import streamlit as st
from backend import chatbot
from langchain_core.messages import HumanMessage

CONFIG = {'configurable': {'thread_id': 'thread-1'}}

# message_history = [] ## as we press enter in our chatbot whole code runs from beginning making message history empty again and again
# to prevent this we use st.session_state(a dictionary) it maintains the history even after rerun

if 'message_history' not in st.session_state:
  st.session_state['message_history']=[]

# loading the conversation history
for message in st.session_state['message_history']:
  with st.chat_message(message['role']):
    st.text(message['content'])



user_input = st.chat_input("Type here .....")

if user_input:

  st.session_state['message_history'].append({'role':'user','content':user_input})
  with st.chat_message('user'):
    st.text(user_input)

  
  response = chatbot.invoke({'messages': [HumanMessage(content=user_input)]}, config=CONFIG)
  ai_message = response['messages'][-1].content

  st.session_state['message_history'].append({'role':'assistant','content':ai_message})
  with st.chat_message('assistant'):
    st.text(ai_message)







