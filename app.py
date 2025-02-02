import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain


def get_vectorstore_from_url(url, openai_api_key):
    # get the text in document form
    loader = WebBaseLoader(url)
    document = loader.load()
    
    # split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter()
    document_chunks = text_splitter.split_documents(document)
    
    # create a vectorstore from the chunks
    vector_store = Chroma.from_documents(document_chunks, OpenAIEmbeddings(api_key=openai_api_key))

    return vector_store


def get_context_retriever_chain(vector_store, openai_api_key):
    llm = ChatOpenAI(api_key=openai_api_key)
    
    retriever = vector_store.as_retriever()
    
    prompt = ChatPromptTemplate.from_messages([
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
      ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation")
    ])
    
    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)
    
    return retriever_chain


def get_conversational_rag_chain(retriever_chain, openai_api_key): 
    llm = ChatOpenAI(api_key=openai_api_key)
    
    prompt = ChatPromptTemplate.from_messages([
      ("system", "Answer the user's questions based on the below context:\n\n{context}"),
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
    ])
    
    stuff_documents_chain = create_stuff_documents_chain(llm, prompt)
    
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)


def get_response(user_input, openai_api_key):
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store, openai_api_key)
    conversation_rag_chain = get_conversational_rag_chain(retriever_chain, openai_api_key)
    
    response = conversation_rag_chain.invoke({
        "chat_history": st.session_state.chat_history,
        "input": user_input
    })
    
    return response['answer']


# app config
st.set_page_config(page_title="Chat with websites", page_icon="🤖")
st.title("Chat with Any Websites")
st.subheader("_This app allows you to chat with any website by providing its URL & OpenAI key._")


# sidebar
with st.sidebar:
    st.header("Configuration:")
    openai_api_key = st.text_input("Enter OpenAI API Key", type="password")
    website_url = st.text_input("Website URL")

if openai_api_key is None or openai_api_key == "":
    st.info("Please enter your OpenAI API key")
elif website_url is None or website_url == "":
    st.info("Please enter a website URL")

else:
    # session state
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = openai_api_key

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="Hello! How can I help you?"),
        ]
    
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = get_vectorstore_from_url(website_url, openai_api_key)

    # user input
    user_query = st.chat_input("Type your message here...")
    
    if user_query is not None and user_query != "":
        response = get_response(user_query, st.session_state.openai_api_key)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))

    # conversation display
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)


# mention the credits
st.sidebar.markdown("---")
st.sidebar.markdown("Built with ❤️ by Piyush Joshi")
