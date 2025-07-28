from typing import Any

from source.dev_logger import debug, measure_time
from source.locations_and_config import data_dir, config
from langchain_community.cache import SQLiteCache
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.storage import LocalFileStore
from langchain.embeddings.cache import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

# 1️⃣ Underlying OpenAI embeddings model


chat_cache: Any = SQLiteCache(database_path=data_dir/"llm_cache.db")  # persists on disk :contentReference[oaicite:0]{index=0}
# 2️⃣ Local filesystem store (creates ./embeddings_cache/)
emb_store = LocalFileStore(data_dir/ "embeddings_cache")


gemini_flash_2_5_thinking_model = ChatGoogleGenerativeAI(
model="gemini-2.5-flash",#model="gemini-2.5-flash-preview-04-17"
	cache =chat_cache,
	google_api_key = config.gemini_api_key,

)
gemini_flash_2_5_no_thinking_model = ChatGoogleGenerativeAI(
model="gemini-2.5-flash",#model="gemini-2.5-flash-preview-04-17"
thinking_budget=0,
	cache =chat_cache,
	google_api_key = config.gemini_api_key,
)
gemini_flash_lite_2_5_thinking_model = ChatGoogleGenerativeAI(
# model="gemini-2.5-flash-preview-04-17",
model="gemini-2.5-flash-lite",#model="gemini-2.5-flash-preview-04-17"
	cache =chat_cache,
	google_api_key = config.gemini_api_key,

)
gemini_flash_lite_2_5_no_thinking_model = ChatGoogleGenerativeAI(
# model="gemini-2.5-flash-preview-04-17",
model="gemini-2.5-flash-lite",#model="gemini-2.5-flash-preview-04-17"
thinking_budget=0,
	cache =chat_cache,
	google_api_key = config.gemini_api_key,
)

base_embeddings = OpenAIEmbeddings(openai_api_key=config.openai_api_key)
default_cheapest_model = gemini_flash_2_5_no_thinking_model
default_thinking_model = gemini_flash_2_5_thinking_model
# 3️⃣ Wrap it so document (and query) embeddings get cached to disk
cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings=base_embeddings,
    document_embedding_cache=emb_store,
    namespace=base_embeddings.model,   # e.g. "text-embedding-ada-002"
    batch_size=100,                         # tune as needed
    query_embedding_cache=True,             # also cache embed_query calls
key_encoder              = "sha256",
)











