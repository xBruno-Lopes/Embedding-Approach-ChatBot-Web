import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplates import css, bot_template, user_template
from langchain.llms import HuggingFaceHub

# Armazenando o ID de sessão do usuário
if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4()
    
# Função para extrair os texto dos PDFs do usuário.
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in os.listdir(pdf_docs):
        pdf_reader = PdfReader(os.path.join(pdf_docs, pdf))
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

# Função para coletar os "pedaços" dos textos dos PDFs.
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Função para transformar os "pedaços" dos textos dos PDFs em vetores.
def get_vectorstore(text_chunks):
    embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

# Função onde é passado os vetores como paramêntro
def get_conversation_chain(vectorstore):
    print(vectorstore.as_retriever())
    llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain

# Função para tratar as mensagens do usuário e Bot do chat.
def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']
    
    with open(f'logs/chat_{st.session_state["session_id"]}.txt', 'a', encoding='utf-8') as f:
            f.write(f'Usuario: {st.session_state.chat_history[-2].content}\n')
            f.write(f'Modelo: {st.session_state.chat_history[-1].content}\n')
    
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def main():
    
    user_question = None
    # Dontenv para carregas as keys no .env
    load_dotenv()
    
    # Setando as configurações da página
    st.set_page_config(page_title="My Personal ChatBot", page_icon=":books:")
    
    # Setando o estilo da página com o CSS
    st.write(css, unsafe_allow_html=True)
    
    # Tratamento para saber se o usuário ou bot mandaram uma mensagem
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if 'chat_iniciado' not in st.session_state:
        st.session_state['chat_iniciado'] = False
        
    st.header("My Personal ChatBot :books:")
    
    # Barra lateral com opções para o usuário
    with st.sidebar:
        st.subheader("Menu")
        
        # Ler os PDFs do usuário
        pdf_docs = "books"
        if st.button("Iniciar Chat"):
            with st.spinner("Processando!"):
                # Coleta o texto
                raw_text = get_pdf_text(pdf_docs)

                # Coleta od "pedaços" dos textos
                text_chunks = get_text_chunks(raw_text)

                # Converte os textos para vetores e salva
                vectorstore = get_vectorstore(text_chunks)

                # Cria a conversação do chat
                st.session_state.conversation = get_conversation_chain(vectorstore)
            
            st.session_state['chat_iniciado'] = True
            st.subheader("Chat pronto para uso!")
    
    if st.session_state['chat_iniciado']:
        # Se o chat foi iniciado, renderiza a caixa de texto
        user_question = st.text_input("Faça uma pergunta:")
        if user_question:
            handle_userinput(user_question)
    else:
        # Caso contrário, mostra um aviso ao usuário
        st.warning("Por favor, inicie o chat antes de mandar sua mensagem!")
    
if __name__ == '__main__':
    main()
