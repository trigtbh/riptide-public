# DNI

import discord
import random
import datetime
import os
import json
import settings


def response(resp_type): # only needs footer response for embeds
    options = {
            0: "footer"
        }
    with open(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)), "assets", "responses.json")) as f:
        responses = json.loads(f.read())
    
    response = random.choice(responses[options[resp_type]])
    return response

def embed(title, color=None): # base embed generator for all cog responses
    if color is None:
        color = random.randint(0, 0xffffff)
    botembed = discord.Embed(title=title, color=color)

    botembed.set_footer(text=response(0))
    botembed.timestamp = datetime.datetime.now()
    return botembed


def error(source, errormsg): # error embed generator
    botembed = embed("Error - {}".format(source), color=0xff0000)
    botembed.description = errormsg
    return botembed

def readabledt(ms):
    dt = datetime.timedelta(milliseconds=ms)
    days = dt.days
    hours = dt.seconds // 3600
    minutes = (dt.seconds % 3600) // 60
    seconds = dt.seconds % 60
    dtstr = ""
    if days:
        dtstr += f"{days} day{'s' if days > 1 else ''}"
        if hours or minutes or seconds:
            dtstr += ", "
    if hours:
        dtstr += f"{hours} hour{'s' if hours > 1 else ''}"
        if minutes or seconds:
            dtstr += ", "
    if minutes:
        dtstr += f"{minutes} minute{'s' if minutes > 1 else ''}"
        if seconds:
            dtstr += ", "
    if seconds:
        dtstr += f"{seconds} second{'s' if seconds > 1 else ''}"
    return dtstr