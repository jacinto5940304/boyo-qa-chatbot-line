import os
import gdown

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


from huggingface_hub import login, whoami

from config import OPENAI_API_KEY, HF_TOKEN


# Constants

folder_url = 'https://drive.google.com/drive/folders/10qfQwhEymw-yOugiO7z3_80cUCiPAmjw?usp=sharing'
output_path = './data'
MODEL_NAME = "gpt-4o"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

system_prompt = (
    "你是規章QA機器人, 目的是為了將複雜的規章用淺顯易懂的方式回答，並熟知規章出處為何，"
    "回答所使用的語言一定要是zh-tw"
    "如果你無法在 context 中找到足夠資訊，請明確回答 'unsure' 即可"
    "Context: {context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

model_kwargs = {'trust_remote_code': True}
encode_kwargs = {'normalize_embeddings': False}

# models init

_docs = None
_llm = None
_embeddings_model = None
_vector_store = None
_retriever = None
_question_answer_chain = None
_chain = None

# functions

def hf_login() -> None:
    login(token=HF_TOKEN, add_to_git_credential=True)

def is_login() -> bool:
    try:
        info = whoami()
        return True
    except:
        return False
    
def download_drive(folder_url: str, output_path: str):
    gdown.download_folder(url=folder_url, output=output_path, quiet=False, use_cookies=False)

def generate_document() -> list[Document]:
    refs = []
    for filename in os.listdir("./data"):
        if filename.endswith(".txt"):
            with open("./data/"+filename, "r", encoding="utf-8") as f:
                refs.extend(list((filter(lambda x: x,f.read().split('\n')))))
    # remove spaces in every string
    for i in range(len(refs)):
        refs[i] = refs[i].replace(" ", "")

    docs = [Document(page_content=doc, metadata={"id": i}) for i, doc in enumerate(refs)]
    return docs

def get_chain():
    global _docs, _llm, _embeddings_model, _vector_store, _retriever, _question_answer_chain, _chain
    if _docs is None:
        try:
            _docs = generate_document()
        except:
            download_drive(folder_url, output_path)
            _docs = generate_document()
    if _llm is None:
        _llm = ChatOpenAI(
            openai_api_key=OPENAI_API_KEY,
            model_name=MODEL_NAME,
            temperature=0.7
        )
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
        )
    # if _vector_store is None:
    #     _vector_store = Chroma.from_documents(
    #         documents=_docs,
    #         embedding=_embeddings_model
    #     )
    if _vector_store is None:
        persist_dir = "./chroma_db"
        if os.path.exists(persist_dir) and os.listdir(persist_dir):
            # 已存在資料庫就讀取
            _vector_store = Chroma(
                embedding_function=_embeddings_model,
                persist_directory=persist_dir
            )
        else:
            # 第一次生成資料庫
            _vector_store = Chroma.from_documents(
                documents=_docs,
                embedding=_embeddings_model,
                persist_directory=persist_dir
            )
            _vector_store.persist()

    if _retriever is None:
        _retriever = _vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 5}
        )
    if _question_answer_chain is None:
        _question_answer_chain = create_stuff_documents_chain(_llm, prompt)
    if _chain is None:
        _chain = create_retrieval_chain(_retriever, _question_answer_chain)

    return _chain

def get_response(query: str) -> dict:
    """
    return value format
    {
        'input': query
        'context': top k related context
        'answer': response from llm
    }
    """
    chain = get_chain()
    return chain.invoke({"input": query})


# main code

if(not is_login()):
    hf_login()

res = get_response("基金會叫什麼名字")


print()
print(res)


# /////////////////////////////////////////////////////////////////////////////////////

# how to use
# call res = get_response('your question')
# Use res['answer'] to get the response in string
# If you want to know the return value in detail, please refer to functions doc string

# /////////////////////////////////////////////////////////////////////////////////////