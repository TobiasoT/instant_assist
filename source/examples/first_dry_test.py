import asyncio
import contextlib
import time
import faulthandler
import traceback

faulthandler.enable()
from fastapi import FastAPI

from source.agents.default_search_agent import CategoryQueryUpdateAgent
from source.create_summary.query_pool import AgentTaskQueryResult, AllowedTypesOfAnswers
from source.create_summary.summary_board import app, SummaryBoard, summary_board
from source.create_summary.summary_of_message_summaries import SummaryOfMessageSummaries
from source.dev_logger import measure_time, debug, mexit
from source.pydantic_models.message import Message


async def main(messages: list[Message]):
	category_query_update_agent = CategoryQueryUpdateAgent()
	summary_of_messages = SummaryOfMessageSummaries(category_query_update_agent = category_query_update_agent,
	                                                assistence_instructions = "I am tom. I am salesperson that wants to sell solar roofs to customers jerry. Please provide me with information that helps me to sell solar roofs to jerry. "
	                                                                       "You may also provide tips what to ask next."
	                                                )
	
	for message in messages:
		await summary_of_messages.update_messages(message)
	
	return []


def create_messages():
	# This function would create and return a list of Message objects.
	# For the sake of this example, we will return an empty list.
	
	texts = ["hello", "how are you?", "i am fine", "what about you?", "how was your day?", "it was good", "what did you do?", "i went to the park", "it was nice", "i saw some friends", "we had a good time", "we played some games",
	         "we talked about life", "it was a good day", "i am happy now", "i hope you are too"]
	people = ["Tom", "Jerry"]
	result = []
	for text in texts:
		measure_time(text = False)
		current_person = people[(len(result) + 1) % len(people)]
		result.append(Message(
			conversation_id = "12345",
			sender = current_person,
			content = text,
			previous_message = result[-1] if result else None,
		))
		measure_time()
	return result


def create_messages_from_json(conversation_jason: list[dict]):
	# This function creates Message objects from a given conversation in JSON format.
	result = []
	for entry in conversation_jason:
		sender = entry["speaker"]
		content = entry["message"]
		previous_message = result[-1] if result else None
		result.append(Message(
			conversation_id = "12345",
			sender = sender,
			content = content,
			previous_message = previous_message,
		))
	return result


conversation_json = [
	{
		"speaker": "Jerry",
		"message": "Hi Tom, thanks for taking the time to meet with me today. I’ve been looking into solar solutions, and I’m particularly interested in a solar roof for my home. By the way, I love Beethoven."
	},
	{
		"speaker": "Tom",
		"message": "Absolutely, Jerry. I’m glad you reached out. Let’s start with what’s driving your interest in a solar roof—are you primarily focused on lowering your energy bills, reducing your carbon footprint, or both?"
	},
	{
		"speaker": "Jerry",
		"message": "A bit of both, actually. I’ve read that solar roofs can generate enough electricity to cover most of a household’s needs, and I want to take advantage of that. Plus, I don’t want to worry about noisy panels sticking up on my shingles—I like the sleek look of an integrated solar roof."
	},
	{
		"speaker": "Tom",
		"message": "That makes sense. Our solar roofs use high-efficiency photovoltaic tiles that look just like traditional roofing materials, so there’s no bulky rack-mounted system. They blend in seamlessly, and they’re backed by a 25-year warranty for both power output and weatherproofing."
	},
	{
		"speaker": "Jerry",
		"message": "That warranty sounds reassuring. Can you tell me more about the tile efficiency and overall expected output?"
	},
	{
		"speaker": "Tom",
		"message": "Of course. Each solar tile has an efficiency of about 22–23%, which is on par with top-tier solar panels. For an average 2,000 ft² roof in Berlin receiving roughly 1,000 kWh/m²/year of solar irradiance, you can expect around 5,000 kWh of annual generation. That typically covers 80–90% of a household’s consumption, depending on your usage patterns."
	},
	{
		"speaker": "Jerry",
		"message": "That’s impressive. I live in a three-bedroom, two-bath home and my annual energy use is close to 4,500 kWh. So this system should cover me fully?"
	},
	{
		"speaker": "Tom",
		"message": "Yes, it would. We tailor the system size to your actual consumption. If you’d like full net-zero operation, we’d size it for 5,000 kWh/year, giving you a small surplus to export to the grid. Anything you don’t use can be credited back, further lowering your bills."
	},
	{
		"speaker": "Jerry",
		"message": "Sounds good. Let’s talk costs—what’s the ballpark price for a roof like that?"
	},
	{
		"speaker": "Tom",
		"message": "For a system sized to produce 5,000 kWh annually, you’re looking at around €25,000 to €28,000 installed. That includes the solar tiles, inverters, monitoring system, and full roof replacement. After federal and state incentives, you could see up to 40% off—bringing your net investment closer to €15,000–€17,000."
	},
	{
		"speaker": "Jerry",
		"message": "A 40% rebate is substantial. What about financing options?"
	},
	{
		"speaker": "Tom",
		"message": "We partner with several green-energy lenders offering low-interest loans specifically for solar installations, starting as low as 1.5% APR over 10–15 years. Many customers find their monthly loan payment is less than their previous power bill, so they cash-flow immediately."
	},
	{
		"speaker": "Jerry",
		"message": "That’s appealing. Are there any maintenance requirements?"
	},
	{
		"speaker": "Tom",
		"message": "Very minimal. The tiles are durable tempered glass, so they’re self-cleaning in most weather. We recommend a professional inspection every five years just to check seals and electrical connections—usually under €200."
	},
	{
		"speaker": "Jerry",
		"message": "Great. How long does installation take?"
	},
	{
		"speaker": "Tom",
		"message": "From permitting to final inspection, about 8–10 weeks. Actual on-site work is 3–4 days for a typical home. We handle all the paperwork and grid-connection approvals for you."
	},
	{
		"speaker": "Jerry",
		"message": "Perfect. Next steps?"
	},
	{
		"speaker": "Tom",
		"message": "I’ll conduct a site survey to verify your roof’s orientation and shading. That’s free and takes about an hour. Once we finalize the design, I’ll send you a detailed proposal with all costs, savings projections, and financing terms. Then, we can schedule the installation."
	},
	{
		"speaker": "Jerry",
		"message": "Let’s do it. When can you come by for the survey?"
	},
	{
		"speaker": "Tom",
		"message": "How about next Tuesday at 2 PM? If that works, I’ll send you a confirmation email with a checklist of what we need—utility bills, roof access details, and so on."
	},
	{
		"speaker": "Jerry",
		"message": "Tuesday at 2 PM works perfectly. Thanks, Tom—I’m excited to get started."
	},
	{
		"speaker": "Tom",
		"message": "Fantastic, Jerry. I’ll see you then and we’ll get you well on your way to an energy-independent home!"
	}
]


# asyncio.run(main(create_messages_from_json(conversation_json)))  # Example usage with a list of Message objects_gute_nacht



if __name__ == "__main__":
	messages = create_messages_from_json(conversation_json)
	category_query_update_agent = CategoryQueryUpdateAgent()
	summary_of_messages = SummaryOfMessageSummaries(category_query_update_agent = category_query_update_agent,
	                                                assistence_instructions = "I am tom. I am salesperson that wants to sell solar roofs to customers jerry. Please provide me with information that helps me to sell solar roofs to jerry. "
	                                                                       "You may also provide tips what to ask next.",
	                                                summary_board = None#summary_board
	                                                )
	async def update_loop() -> None:
		for message in messages:
			debug(f"Updating summary of messages with: \n{message.sender}: {message.content}")
			await summary_of_messages.update_messages(message)
			await asyncio.sleep(0.5)
		await asyncio.sleep(1.5)
	# try:
	# 	asyncio.run(update_loop())  # Run the update loop to process messages
	# except Exception:
	# 	traceback.print_exc()
	# mexit()
	summary_of_messages.summary_board = summary_board
	@contextlib.asynccontextmanager
	async def lifespan(app: FastAPI):
		# → startup logic_run
		debug("🟢 Starting update loop…")
	
		loop_task = asyncio.create_task(update_loop())
		try:
			yield
		finally:
			debug("🔴 Stopping update loop…")
			loop_task.cancel()
			with contextlib.suppress(asyncio.CancelledError):
				await loop_task

	import uvicorn
	
	app.router.lifespan_context = lifespan  # attach lifespan after app creation
	uvicorn.run(
		app = app,
		host = "0.0.0.0",  # or "127.0.0.1"
		port = 8000,
		reload = False,  # no auto-reload
		log_level = "info",
	)
