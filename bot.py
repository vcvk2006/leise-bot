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
app = Flask('')

@app.route('/')
def home():
    return "Leise bot is alive!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def start_web_server_thread():
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()


# --- Discord Bot Configuration ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("Error: DISCORD_TOKEN not found. Please add it to your environment variables.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# --- Helper Function for Parsing ---
def parse_arguments(args_str: str):
    """Parses a string of arguments into a dictionary."""
    try:
        # Use shlex to handle quoted strings correctly
        split_args = shlex.split(args_str)
        # Create a dictionary from key=value pairs
        return {key.lower(): value for key, value in (arg.split('=', 1) for arg in split_args if '=' in arg)}
    except ValueError:
        return None

# --- Bot Events ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Leise is ready to send and edit messages!')
    print('------')


# --- Bot Commands ---
@bot.command(
    name='leise',
    help='''Sends a customizable message or embed.
    
    Usage Examples:
    !leise message="Hello world"
    !leise channel=#general message="This is for the general channel."
    !leise message="Check this out!" link_text="Docs" link="https://discordpy.readthedocs.io/"
    '''
)
async def send_custom_message(ctx, *, args: str = None):
    if not args:
        return await ctx.send("`Error:` You must provide arguments. Use `!help leise` for examples.")

    parsed_args = parse_arguments(args)
    if parsed_args is None:
        return await ctx.send("`Error:` Could not parse arguments. Please check your quotes.")

    message_content = parsed_args.get('message')
    if not message_content:
        return await ctx.send("`Error:` You must provide a `message` argument.")

    target_channel = ctx.channel
    if 'channel' in parsed_args:
        try:
            channel_id = int(re.search(r'<#(\d+)>', parsed_args['channel']).group(1))
            found_channel = bot.get_channel(channel_id)
            if found_channel:
                target_channel = found_channel
            else:
                return await ctx.send(f"`Error:` Could not find the channel {parsed_args['channel']}.")
        except (AttributeError, ValueError):
            return await ctx.send("`Error:` Invalid channel format. Please mention the channel (e.g., #general).")

    link = parsed_args.get('link')
    link_text = parsed_args.get('link_text')
    thumbnail = parsed_args.get('thumbnail')
    footer = parsed_args.get('footer')

    # If no embed options are provided, send a simple message
    if not any([link, link_text, thumbnail, footer]):
        await target_channel.send(message_content)
    else: # Otherwise, build and send an embed
        embed = discord.Embed(color=discord.Color.from_rgb(112, 161, 224))
        description = message_content
        if link and link_text:
            description += f"\n\n**[{link_text}]({link})**"
        elif link:
            description += f"\n\n**[{link}]({link})**"
        
        embed.description = description

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if footer:
            embed.set_footer(text=footer)
        
        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            return await ctx.send(f"`Error:` I don't have permission to send messages in {target_channel.mention}.")
        except discord.HTTPException as e:
            return await ctx.send(f"`Error:` Failed to send the embed. Details: {e}")

    if target_channel != ctx.channel:
        await ctx.send(f"Message sent to {target_channel.mention}!", delete_after=5)


@bot.command(
    name='edit',
    help='''Edits a message previously sent by Leise.
    
    Usage:
    !edit <message_link> message="New content" footer="Updated footer"
    '''
)
async def edit_message(ctx, message_link: str = None, *, args: str = None):
    if not message_link or not args:
        return await ctx.send("`Error:` You must provide a message link and arguments to edit. Use `!help edit`.")

    # Regex to extract channel and message IDs from the link
    match = re.search(r'/channels/\d+/(\d+)/(\d+)', message_link)
    if not match:
        return await ctx.send("`Error:` Invalid message link provided.")

    channel_id, message_id = map(int, match.groups())
    
    try:
        target_channel = bot.get_channel(channel_id)
        if not target_channel:
            return await ctx.send("`Error:` I can't find that channel.")
        
        original_message = await target_channel.fetch_message(message_id)
    except discord.NotFound:
        return await ctx.send("`Error:` Could not find the message. Is the link correct?")
    except discord.Forbidden:
        return await ctx.send("`Error:` I don't have permission to access that message.")

    # Ensure the bot is only editing its own messages
    if original_message.author != bot.user:
        return await ctx.send("`Error:` I can only edit messages that I have sent.")

    parsed_args = parse_arguments(args)
    if parsed_args is None:
        return await ctx.send("`Error:` Could not parse arguments. Please check your quotes.")

    # Get the new content, or use the old content if not provided
    new_content = parsed_args.get('message')
    if new_content is None:
        # If the original was an embed, get its description
        if original_message.embeds:
            new_content = original_message.embeds[0].description.split('\n\n**[')[0]
        else:
            new_content = original_message.content

    link = parsed_args.get('link')
    link_text = parsed_args.get('link_text')
    thumbnail = parsed_args.get('thumbnail')
    footer = parsed_args.get('footer')

    # If no embed options are provided, edit to a simple message
    if not any([link, link_text, thumbnail, footer]):
        await original_message.edit(content=new_content, embed=None)
    else: # Otherwise, build and edit the embed
        embed = discord.Embed(color=discord.Color.from_rgb(112, 161, 224))
        description = new_content
        if link and link_text:
            description += f"\n\n**[{link_text}]({link})**"
        elif link:
            description += f"\n\n**[{link}]({link})**"
        
        embed.description = description

        # Use new thumbnail/footer if provided, otherwise keep the old one
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        elif original_message.embeds and original_message.embeds[0].thumbnail:
            embed.set_thumbnail(url=original_message.embeds[0].thumbnail.url)

        if footer:
            embed.set_footer(text=footer)
        elif original_message.embeds and original_message.embeds[0].footer:
            embed.set_footer(text=original_message.embeds[0].footer.text)

        await original_message.edit(content=None, embed=embed)

    await ctx.send("Message edited successfully!", delete_after=5)


# --- Main Execution ---
if __name__ == "__main__":
    start_web_server_thread()
    bot.run(TOKEN)
