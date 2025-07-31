# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import shlex
import re
from flask import Flask
from threading import Thread

# --- Flask Web Server (for Render Hosting) ---
# This small web server is necessary to keep the Render service alive.
# Render's free tier web services go to sleep if they don't receive traffic.
# This server responds to Render's health checks.
app = Flask('')

@app.route('/')
def home():
    return "Leise bot is alive!"

def run_web_server():
    # The host must be '0.0.0.0' to be accessible by Render
    # The port is provided by the PORT environment variable on Render
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def start_web_server_thread():
    # Run the web server in a separate thread so it doesn't block the bot
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True # Allows main thread to exit even if this thread is running
    server_thread.start()


# --- Discord Bot Configuration ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN not found. Please create a .env file or add it to Render's environment variables.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# --- Bot Events ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Leise is ready to send messages!')
    print('------')


# --- Bot Commands ---
@bot.command(
    name='leise',
    help='''Sends a customizable message or embed to a specified channel.

    Usage Examples:
    !leise message="Hello world"
    !leise channel=#general message="This is for the general channel."
    !leise message="Check this out!" link_text="Docs" link="https://discordpy.readthedocs.io/"
    '''
)
async def send_custom_message(ctx, *, args: str = None):
    if not args:
        await ctx.send("`Error:` You must provide arguments. Use `!help leise` for examples.")
        return

    try:
        split_args = shlex.split(args)
        parsed_args = {key.lower(): value for key, value in (arg.split('=', 1) for arg in split_args if '=' in arg)}
    except ValueError as e:
        await ctx.send(f"`Error:` Could not parse arguments. Please check your quotes. Details: {e}")
        return

    message = parsed_args.get('message')
    if not message:
        await ctx.send("`Error:` You must provide a `message` argument.")
        return

    target_channel = ctx.channel
    channel_arg = parsed_args.get('channel')
    if channel_arg:
        try:
            channel_id = int(re.search(r'<#(\d+)>', channel_arg).group(1))
            found_channel = bot.get_channel(channel_id)
            if found_channel:
                target_channel = found_channel
            else:
                await ctx.send(f"`Error:` Could not find the channel {channel_arg}.")
                return
        except (AttributeError, ValueError):
            await ctx.send(f"`Error:` Invalid channel format. Please mention the channel (e.g., #general).")
            return

    link = parsed_args.get('link')
    link_text = parsed_args.get('link_text')
    thumbnail = parsed_args.get('thumbnail')
    footer = parsed_args.get('footer')

    if not any([link, link_text, thumbnail, footer]):
        await target_channel.send(message)
    else:
        embed = discord.Embed(color=discord.Color.from_rgb(112, 161, 224))
        description = message
        if link and link_text:
            description += f"\n\n**[{link_text}]({link})**"
        elif link:
            description += f"\n\n**[{link}]({link})**"
        elif link_text:
            await ctx.send("`Error:` You provided `link_text` but no `link`.")
            return
        
        embed.description = description

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if footer:
            embed.set_footer(text=footer)
        
        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"`Error:` I don't have permission to send messages in {target_channel.mention}.")
        except discord.HTTPException as e:
            await ctx.send(f"`Error:` Failed to send the embed. Details: {e}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")

    if channel_arg and target_channel != ctx.channel:
        await ctx.send(f"Message sent to {target_channel.mention}!", delete_after=5)


# --- Main Execution ---
if __name__ == "__main__":
    # Start the web server in a background thread
    start_web_server_thread()
    
    # Start the bot
    bot.run(TOKEN)
