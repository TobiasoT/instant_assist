import os
from pydantic import BaseModel
from pathlib import Path
from source.dev_logger import debug

project_root_dir = Path(__file__).parent.parent
resources_dir = project_root_dir / "resources"
resources_dir.mkdir(exist_ok=True)
data_dir = project_root_dir / "data"
data_dir.mkdir(exist_ok=True)

templates_dir = resources_dir / "templates"
path_live_kit_index_html = templates_dir / "livekit_index.html"
path_summary_board_html = templates_dir / "summary_board.html"
path_static_dir = resources_dir / "static"
path_static_css_dir = path_static_dir / "css"
path_static_js_dir = path_static_dir / "js"

path_agent_js = path_static_js_dir / "agent.js"
path_agent_css = path_static_css_dir / "agent.css"

path_persistence_dir = data_dir / "persistence"

class Config(BaseModel):
	livekit_room_name: str = "Default Room"
	livekit_ws_url: str
	livekit_api_key: str
	livekit_api_secret: str
	assembly_ai_listener_name: str = "livekit-listener"
	assemblyai_api_key: str
	gemini_api_key: str
	openai_api_key: str

def load_config() -> Config:
	path_to_config = data_dir / "config.json"
	
	config_data = {}
	if path_to_config.exists():
		try:
			config_data = Config.model_validate_json(path_to_config.read_text()).model_dump()
		except Exception as e:
			debug(f"Could not load config.json: {e}")
	
	env_overrides = {
		"livekit_ws_url": os.getenv("LIVEKIT_WS_URL"),
		"assemblyai_api_key": os.getenv("ASSEMBLYAI_API_KEY"),
		"gemini_api_key": os.getenv("GEMINI_API_KEY"),
		"openai_api_key": os.getenv("OPENAI_API_KEY"),
		"livekit_api_key": os.getenv("LIVEKIT_API_KEY"),
		"livekit_api_secret": os.getenv("LIVEKIT_API_SECRET"),
	}
	
	for key, value in env_overrides.items():
		if value:
			config_data[key] = value
	
	config = Config(**config_data)
	
	try:
		safe_config = config.model_dump()
		for key in ["assemblyai_api_key", "gemini_api_key", "openai_api_key"]:
			if key in safe_config and safe_config[key]:
				safe_config[key] = safe_config[key][:8] + "..." if len(safe_config[key]) > 8 else "***"
		
		path_to_config.write_text(Config(**{k: v for k, v in config.model_dump().items()}).model_dump_json(indent=4))
	except Exception as e:
		debug(f"Could not write config.json: {e}")
	
	return config

def config_to_env(config: Config):
	os.environ["LIVEKIT_WS_URL"] = config.livekit_ws_url
	os.environ["ASSEMBLYAI_API_KEY"] = config.assemblyai_api_key
	os.environ["GEMINI_API_KEY"] = config.gemini_api_key
	os.environ["OPENAI_API_KEY"] = config.openai_api_key
	os.environ["LIVEKIT_API_KEY"] = config.livekit_api_key
	os.environ["LIVEKIT_API_SECRET"] = config.livekit_api_secret

config = load_config()

uploads_dir = path_persistence_dir / "uploads"
quick_access_info = uploads_dir / "quick_access_context.txt"
