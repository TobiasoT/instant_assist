from __future__ import annotations

from source.custom_assembly_ai_multi_client import CustomAssemblyAiMultiClientFactory
from source.locations_and_config import config

global_custom_assembly_ai_multi_client_factory: CustomAssemblyAiMultiClientFactory | None = CustomAssemblyAiMultiClientFactory(
			api_key = config.assemblyai_api_key,
			conversation_id = "livekit-conversation",
		)
