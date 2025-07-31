# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import shlex
import re

# --- Configuration ---
# Load environment variables from a .env file for security
load_dotenv()
# It's best practice to store your bot token in a .env file
# Create a file named .env in the same directory and add the line:
# DISCORD_TOKEN="YOUR_BOT_TOKEN_HERE"
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN not found. Please create a .env file and add your bot token.")
    exit()

# --- Bot Setup ---
# Define the bot's intents. These are permissions for what the bot can listen to.
# 'message_content' is required for the bot to read messages.
intents = discord.Intents.default()
intents.message_content = True

# Create the bot instance with a command prefix '!' and the defined intents.
# The bot's name is Leise, but the command prefix can be anything you like.
bot = commands.Bot(command_prefix='!', intents=intents)


# --- Events ---
@bot.event
async def on_ready():
    """
    This event is triggered once the bot has successfully connected to Discord.
    It prints a confirmation message to your console.
    """
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Leise is ready to send messages!')
    print('------')


# --- Commands ---
@bot.command(
    name='leise',
    help='''Sends a customizable message or embed to a specified channel.

    Usage Examples:
    1. Simple Message (in current channel):
       !leise message="Hello, this is a plain text message."

    2. Simple Message (in a specific channel):
       !leise channel=#general message="This message is for the general channel."

    3. Message with a Custom Link:
       !leise channel=#announcements message="Check out the official docs!" link_text="Discord.py Docs" link="https://discordpy.readthedocs.io/"

    4. Message with a Thumbnail:
       !leise message="Here is a cool image." thumbnail="https://i.imgur.com/axIm24I.png"

    5. Message with a Footer:
       !leise message="This message has a footer." footer="Sent via Leise Bot"

    6. All Features Combined (in a specific channel):
       !leise channel=#random message="This is a full embed example." link_text="Click Me" link="https://google.com" thumbnail="https://i.imgur.com/axIm24I.png" footer="This is the footer."
    '''
)
async def send_custom_message(ctx, *, args: str = None):
    """
    A flexible command that manually parses arguments for robustness.
    It can send plain text or a rich embed.
    """
    if not args:
        await ctx.send("`Error:` You must provide arguments. Use `!help leise` for examples.")
        return

    # Use shlex to split arguments safely, respecting quotes
    try:
        split_args = shlex.split(args)
        parsed_args = {}
        for arg in split_args:
            parts = arg.split('=', 1)
            if len(parts) == 2:
                key = parts[0].lower()
                value = parts[1]
                parsed_args[key] = value
            else:
                # Handle potential malformed arguments if necessary
                pass
    except ValueError as e:
        await ctx.send(f"`Error:` Could not parse arguments. Please check your quotes. Details: {e}")
        return

    message = parsed_args.get('message')
    if not message:
        await ctx.send("`Error:` You must provide a `message` argument. Example: `!leise message=\"Hello world\"`")
        return

    # Determine the target channel
    target_channel = ctx.channel
    channel_arg = parsed_args.get('channel')
    if channel_arg:
        try:
            # Extract channel ID from mention, e.g., <#123456789>
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

    # Case 1: Just a simple message.
    if not link and not link_text and not thumbnail and not footer:
        await target_channel.send(message)
        if channel_arg:
            await ctx.send(f"Message sent to {target_channel.mention}!", delete_after=5)
        return

    # Case 2: An embed is needed.
    embed = discord.Embed(color=discord.Color.from_rgb(112, 161, 224))
    description = message
    if link and link_text:
        description += f"\n\n**[{link_text}]({link})**"
    elif link and not link_text:
        description += f"\n\n**[{link}]({link})**"
    elif link_text and not link:
        await ctx.send("`Error:` You provided `link_text` but no `link`.")
        return

    embed.description = description

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if footer:
        embed.set_footer(text=footer)

    try:
        await target_channel.send(embed=embed)
        if channel_arg:
            await ctx.send(f"Message sent to {target_channel.mention}!", delete_after=5)
    except discord.Forbidden:
        await ctx.send(f"`Error:` I don't have permission to send messages in {target_channel.mention}.")
    except discord.HTTPException as e:
        await ctx.send(f"`Error:` Failed to send the embed. Please check your thumbnail URL. Details: {e}")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")


# --- Run the Bot ---
# This line starts the bot using the token from your .env file.
bot.run(TOKEN)
