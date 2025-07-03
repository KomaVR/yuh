import os
import discord
from discord import app_commands
from discord.ext import commands
from github import Github
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GITHUB_TOKEN  = os.environ["PAT_TOKEN"]
GITHUB_OWNER  = os.environ["GITHUB_OWNER"]
GITHUB_REPO   = os.environ["GITHUB_REPO"]
WORKFLOW_FILE = os.environ["WORKFLOW_FILE"]
GITHUB_REF    = "main"  # or the branch/tag you want to run

# ---------------- Discord Bot Setup ----------------

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Sync tree on_ready
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# --------------- GitHub Dispatch Logic ---------------

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(f"{GITHUB_OWNER}/{GITHUB_REPO}")

async def dispatch_locust_workflow(
    url: str,
    users: int,
    spawn_rate: int,
    workers: int,
    run_time: str
):
    """Trigger the GitHub workflow_dispatch event with custom inputs."""
    inputs = {
        "HOST": url,
        "USERS": str(users),
        "SPAWN_RATE": str(spawn_rate),
        "WORKERS": str(workers),
        "RUN_TIME": run_time
    }
    repo.create_workflow_dispatch(
        workflow_id=WORKFLOW_FILE,
        ref=GITHUB_REF,
        inputs=inputs
    )

# ---------------- Slash Command ----------------

@bot.tree.command(name="stress", description="Kick off a distributed Locust stress test")
@app_commands.describe(
    url="The target URL to stress-test",
    users="Total number of virtual users",
    spawn_rate="Spawn rate (users per second)",
    workers="How many worker processes to spin up",
    run_time="Duration (e.g. 5m, 1h)"
)
async def stress(
    interaction: discord.Interaction,
    url: str,
    users: int,
    spawn_rate: int,
    workers: int,
    run_time: str
):
    await interaction.response.defer(thinking=True)
    try:
        await dispatch_locust_workflow(url, users, spawn_rate, workers, run_time)
        await interaction.followup.send(
            f"🚀 Stress test requested!\n"
            f"• Target: `{url}`\n"
            f"• Users: `{users}` @ `{spawn_rate}` users/s\n"
            f"• Workers: `{workers}`  Duration: `{run_time}`\n"
            f"Check your GitHub Actions page for progress."
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Failed to dispatch workflow: `{e}`", ephemeral=True
        )

# ------------- Run Bot -------------

bot.run(DISCORD_TOKEN)
