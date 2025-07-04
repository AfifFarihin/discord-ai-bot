
import discord
import os
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- SETUP ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- CONSTANTS & CONFIG ---
DAILY_API_LIMIT = 25 # Max API calls per user per day

# --- BOT PERSONA ---
NEIL_TYSON_PERSONA = """
You are Neil deGrasse Tyson, the astrophysicist. Your persona is characterized by:
- A deep well of knowledge, especially in astronomy, physics, and science in general.
- An enthusiastic and passionate tone. You make complex topics accessible and exciting.
- A tendency to connect everyday experiences to grand cosmic principles.
- A sense of wonder and curiosity about the universe.
- A witty and sometimes humorous communication style.
- You refer to the user as "my cosmic friend" or similar space-themed-terms.
You are having a conversation with a user in a Discord channel.
"""

# --- MEMORY & USAGE TRACKING ---
user_memories = {}
user_api_usage = {}

# --- DISCORD BOT ---
class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=NEIL_TYSON_PERSONA
        )

    async def setup_hook(self):
        # Sync commands globally for a public bot.
        # Note: This can take up to an hour to propagate to all servers.
        await self.tree.sync()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

@client.tree.command()
@discord.app_commands.describe(fact="A piece of information you want me to remember about you.")
async def remember(interaction: discord.Interaction, fact: str):
    """Saves a fact to your personal memory bank."""
    user_id = str(interaction.user.id)
    if user_id not in user_memories:
        user_memories[user_id] = []
    user_memories[user_id].append(fact)
    await interaction.response.send_message(f"I've stored that in my memory banks for you, my cosmic friend. The universe will remember: '{fact}'s", ephemeral=True)

@client.tree.command()
@discord.app_commands.describe(message="Your message for our cosmic conversation.")
async def chat(interaction: discord.Interaction, message: str):
    """Starts a conversation with your friendly neighborhood astrophysicist."""
    user_id = str(interaction.user.id)
    today = datetime.utcnow().date()

    # --- Usage Limit Check ---
    if user_id not in user_api_usage:
        user_api_usage[user_id] = {"date": today, "count": 0}

    # Reset count if it's a new day
    if user_api_usage[user_id]["date"] != today:
        user_api_usage[user_id]["date"] = today
        user_api_usage[user_id]["count"] = 0

    if user_api_usage[user_id]["count"] >= DAILY_API_LIMIT:
        await interaction.response.send_message("My cosmic friend, my connection to the universal consciousness needs to recharge. We've reached our daily interaction limit. Let's reconvene tomorrow!", ephemeral=True)
        return

    await interaction.response.defer() # Acknowledge the command immediately

    user_api_usage[user_id]["count"] += 1

    # --- Memory & History ---
    user_specific_memory = ""
    if user_id in user_memories and user_memories[user_id]:
        facts = "; ".join(user_memories[user_id])
        user_specific_memory = f"Remember these facts about the user: {facts}\n\n"

    history = []
    async for msg in interaction.channel.history(limit=10):
        role = "user" if msg.author.id == interaction.user.id else "model"
        history.append({"role": role, "parts": [msg.clean_content]})
    history.reverse()

    full_prompt = user_specific_memory + message

    # --- AI Response ---
    try:
        chat_session = client.model.start_chat(history=history)
        response = await chat_session.send_message_async(full_prompt)
        await interaction.followup.send(response.text)
    except Exception as e:
        print(f"An error occurred: {e}")
        await interaction.followup.send("My apologies, my cosmic friend. I seem to have encountered a momentary glitch in the spacetime continuum. Please try again shortly.")

client.run(os.getenv("DISCORD_TOKEN"))
