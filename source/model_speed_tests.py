import time
from typing import Any

from source.dev_logger import debug, measure_time
from source.locations_and_config import openai_api_key, data_dir
from langchain_community.cache import SQLiteCache
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.storage import LocalFileStore
from langchain.embeddings.cache import CacheBackedEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

chat_cache =  None

speed_test_gpt_4_1_model = ChatOpenAI(
	model = "gpt-4.1",
	temperature = 0.0,
	openai_api_key = openai_api_key,
	cache = chat_cache,
)
speed_test_gpt_o4_mini_model= ChatOpenAI(
	model = "o4-mini",
	# temperature = 1,
	openai_api_key = openai_api_key,
	cache = chat_cache,
)
speed_test_gpt_4_1_mini_model= ChatOpenAI(
	model = "gpt-4.1-mini",
	temperature = 0.0,
	openai_api_key = openai_api_key,
	cache = chat_cache,
)
# speed_test_default_human_like_model = ChatOpenAI(
# 	model ="gpt-4.5",# "gpt-4.5-preview",
# 	# temperature = 0.0,
# 	openai_api_key = openai_api_key,
# 	cache = chat_cache,
# )
speed_test_gemini_flash_2_5_thinking_model = ChatGoogleGenerativeAI(
# model="gemini-2.5-flash-preview-04-17",
model="gemini-2.5-flash",#model="gemini-2.5-flash-preview-04-17"
	cache =chat_cache,

)
speed_test_gemini_flash_2_5_no_thinking_model = ChatGoogleGenerativeAI(
# model="gemini-2.5-flash-preview-04-17",
model="gemini-2.5-flash",#model="gemini-2.5-flash-preview-04-17"
thinking_budget=0,
	cache =chat_cache,
)
speed_test_gemini_flash_2_5_lite_no_thinking_model = ChatGoogleGenerativeAI(
# model="gemini-2.5-flash-preview-04-17",
model="gemini-2.5-flash-lite",#model="gemini-2.5-flash-preview-04-17"
thinking_budget=0,
	cache =chat_cache,
)
# response = default_cheapest_model.invoke("What is the capital of France?")


base_embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)


list_of_all_models = [
	# speed_test_default_human_like_model,
	# speed_test_gpt_4_1_model,
	# speed_test_gpt_o4_mini_model,
	# speed_test_gpt_4_1_mini_model,
	# speed_test_gemini_flash_2_5_thinking_model,
	speed_test_gemini_flash_2_5_no_thinking_model,
speed_test_gemini_flash_2_5_lite_no_thinking_model
]

sentences = ["test", "what is the capital of France?", "list all numbers from 1 to 140"]

for model in list_of_all_models:
	for sentence in sentences:
		t=time.time()
		response = model.invoke(sentence)
		name = model.model_name if hasattr(model, 'model_name') else model.__class__.__name__
		debug(f"time taken for {name}: {time.time() - t} seconds, output_words_per_second: {len(response.content.split()) / (time.time() - t)}")
	






