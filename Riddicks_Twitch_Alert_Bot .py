import discord
from discord.ext import commands
import json
import os
import aiohttp
import asyncio

script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "config.json")) as f:
    config = json.load(f)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event 
async def on_ready():
    print(f"{bot.user.name} Is ready online and ready to party!")

    try:
        guild = discord.Object(id=int(config["guild_id"]))
        await bot.tree.sync()
        for cmd in bot.tree.get_commands():
            print(f"Registered command: /{cmd.name} - {cmd.description}")
            
        print(f"Slash commands synced to server ID {config['guild_id']}")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

    bot.loop.create_task(twitch_stream_check_loop())

print("Loading derp ping pong...")

@bot.tree.command(name="derp", description="Test if the bot is working")
async def derp(interaction: discord.Interaction):
    await interaction.response.send_message("merp!")

print("Derp be merpin!")

print("Loading /addstreamer...")

@bot.tree.command(name="ns", description="Track a new Twitch streamer")
@discord.app_commands.describe(
    streamer_name="Twitch username",
    link="Full Twitch link",
    custom_message="Custom message to use when live",
    color="Hex color for the embed (e.g. #FF0000)"
)
async def ns(
    interaction: discord.Interaction,
    streamer_name: str,
    link: str,
    custom_message: str,
    color: str 
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "data.json"), "r") as f:
        data = json.load(f)

    for s in data["streamers"]:
        if s["name"].lower() == streamer_name.lower():
            await interaction.response.send_message(f"'{streamer_name}' is already being tracked", ephemeral=True)
            return
        
    data["streamers"].append({
        "name": streamer_name,
        "link": link,
        "message": custom_message,
        "color": color,
        "is_live": False,
        "last_message_id": None

    })

    with open(os.path.join(script_dir, "data.json"), "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"'{streamer_name}' has been added to the tracked streamers list!", ephemeral=True)

print("/addstreamer command loaded")

print("Loading /list")

@bot.tree.command(name="list", description="List all tracked Twitch streamers.")
async def list_streamers(interaction: discord.Interaction):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "data.json"), "r") as f:
        data = json.load(f)

    if not data["streamers"]:
        await interaction.response.send_message("No streamers are being tracked yet!", ephemeral=True)
        return
    
    msg = "**Currently Tracked Streamers:**\n"
    for s in data["streamers"]:
        msg += f"🎥 [{s['name']}]({s['link']}) - {s['message']}\n"

    await interaction.response.send_message(msg, ephemeral=True)

print(" /list loaded")

print("loading /edit")

@bot.tree.command(name="edit", description="Edit a stteamer's info (name, link, message)")
@discord.app_commands.describe(
    streamer="The name of the streamer",
    field="Which field to edit: name, link, or message",
    new_value="The new value to set"
)
async def edit_streamer(
    interaction: discord.Interaction,
    streamer: str,
    field: str,
    new_value: str
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data.json")

    with open(data_path, "r") as f:
        data = json.load(f)

    for s in data["streamers"]:
        if s["name"].lower() == streamer.lower():
            if field not in ["name", "link", "message", "color"]:
                await interaction.response.send_message("Field must be one of: 'name', 'link', or 'message'.", ephemeral=True)
                return
            
            old_value = s[field]
            s[field] = new_value

            if field == "name":
                s["name"] = new_value

            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

            await interaction.response.send_message(f"'{field}' updated for '{streamer}' !\n**old:** {old_value}\n**New:** {new_value}", ephemeral=True)
            return

    await interaction.response.send_message(f"Streamer '{streamer}' not found in the tracked list.", ephemeral=True) 

print(" /edit loaded")

print("Loading /channel")

@bot.tree.command(name="channel", description="Set the channel for stream notifications")
@discord.app_commands.describe(channel="The channel to post live alerts in")
async def set_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data.json")

    with open(data_path, "r") as f:
        data = json.load(f)

    data["channel_id"] = channel.id

    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"Stream alerts will now be posted in {channel.mention}.", ephemeral=True)

print(" /channel loaded")

print(" Loading /role")

@bot.tree.command(name="role", description="Set the role to ping for stream alerts")
@discord.app_commands.describe(role="The role to ping when someone goes live")
async def set_role(interaction: discord.Interaction, role: discord.Role):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data.json")

    with open(data_path, "r") as f:
        data = json.load(f)

    data["role_id"] = role.id

    with open(data_path, "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"Alerts will now ping the role: {role.mention}", ephemeral=True)

print("leading /remove")

@bot.tree.command(name="remove", description="Stop tracking a Twitch Streamer")
@discord.app_commands.describe(streamer="The name of the streamer to remove")

async def remove_streamer(
    interaction: discord.Interaction,
    streamer: str
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data.json")

    with open(data_path, "r") as f:
        data = json.load(f)

    for s in data["streamers"]:
        if s["name"].lower() == streamer.lower():
            data["streamers"].remove(s)

            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

            await interaction.response.send_message(f"Removed '{streamer}' from the tracked list.", ephemeral=True)
            return
        
    await interaction.response.send_message(f"Streamer '{streamer}' was not found", ephemeral=True)

print(" /remove loaded")

async def get_twitch_token(client_id, client_secret):
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            return data["access_token"]
        
async def twitch_stream_check_loop():
    await bot.wait_until_ready()
    client_id = config["twitch_client_id"]
    client_secret = config["twitch_client_secret"]

    token = await get_twitch_token(client_id, client_secret)
    if not token:
        print("Failed to retrieve Twitch access token")
    else:
        print("Twitch access token obtained")

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}"
    }

    while not bot.is_closed():
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(script_dir, "data.json")
            with open(data_path, "r") as f:
                data = json.load(f)

            channel_id = data.get("channel_id")
            if channel_id is None:
                print("No alert channel set. Skipping Twitch check")
                await asyncio.sleep(60)
                continue

            channel = bot.get_channel(channel_id)
            if channel is None:
                print("Invalid channel ID. Skipping Twitch check.")
                await asyncio.sleep(60)
                continue

            async with aiohttp.ClientSession() as session:
                for streamer in data["streamers"]:
                    user = streamer["name"]
                    url = f"https://api.twitch.tv/helix/streams?user_login={user}"
                    async with session.get(url, headers=headers) as resp:
                        res_data = await resp.json()
                        stream_live = len(res_data.get("data", [])) > 0

                        if stream_live and not streamer.get("is_live"):
                            
                            role_id = data.get("role_id")
                            role_mention = f"<@&{role_id}>" if role_id else ""

                            msg = await channel.send(
                                f"{role_mention} **{user} Is LIVE on Twitch**\n{streamer['message']}\n{streamer['link']}"
                            )

                            streamer["is_live"] = True
                            streamer["last_message_id"] = msg.id
                            
                            with open(data_path, "w") as f:
                                json.dump(data, f, indent=4)

                        elif not stream_live and streamer.get("is_live"):
                            try:
                                msg_id = streamer.get("last_message_id")
                                if msg_id:
                                    old_msg = await channel.fetch_message(msg_id)
                                    await old_msg.edit(content=f"**{user} has gone offline.**")

                            except Exception as e:
                                print(f"Could not edit message: {e}")

                            streamer["is_live"] = False 
                            streamer["last_message_id"] = None

            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Error in Twitch check loop: {e}")

        await asyncio.sleep(60)

print("About to Run bot!")

bot.run(config["discord_token"])
