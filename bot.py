import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os, json
import requests

bot = discord.Client(
    command_prefix = ['!'],
    intents = discord.Intents.all()
)
load_dotenv()

channelID = int(os.getenv('CHANNEL'))

if "last.json" not in os.listdir():
    with open('last.json', 'x') as f:
        f.write('{"inv": [], "darvo": "", "market": []}')

@tasks.loop(seconds = 5)
async def mainLoop():
    embed = discord.Embed(
        title = "Item Notification",
        color = 0x00AAFF
    )

    with open('searchFor.json', 'r') as f:
        searchFor: list[str] = json.load(f) 

    # Get invasions
    invasions = requests.get("https://api.warframestat.us/pc/invasions/").json()

    # Get darvo deal
    darvodeals: list[dict[str, str]] = requests.get("https://api.warframestat.us/pc/dailyDeals/?language=en").json()

    # Get market deals
    marketdeals: list[dict[str, str]] = requests.get("https://api.warframestat.us/pc/flashSales/").json()

    # Get last
    with open('last.json', 'r') as f:
        last: dict[str, list[str]] = json.load(f)

    for keyword in searchFor:
        # Invasion
        for invasion in invasions:
            # Get atker and defer
            for stance in ('attacker', 'defender'):
                try:
                    reward: str = invasion[stance]['reward']['asString'] # its possible to get just the rewardTypes but this is more safer

                    if keyword.lower() in reward.lower() and invasion['id'] not in last['inv'] and not invasion['completed']:
                        embed.add_field(
                            name = "Invasion Alert",
                            value = f"Item: **{reward}**\nMission: {invasion['node']}"
                        )
                        last['inv'].append(invasion['id'])
                except KeyError:
                    continue

        # Darvo deals
        deal = darvodeals[0]
        if keyword.lower() in deal['item'].lower() and deal['item'] != last['darvo']:
            last['darvo'] = deal['item']

            embed.add_field(
                name = "Darvo Deal",
                value = f"Item: **{deal['item']}**\nPrice: **{deal['salePrice']}** ~~{deal['originalPrice']}~~"
            )

        # Market Deals
        for deal in marketdeals:
            if keyword.lower() in deal['item'].lower() and deal['id'] not in last['market'] and not deal['expired']:
                embed.add_field(
                    name = "Market Deal",
                    value = f"Item: **{deal['item']}**\nDiscount: {deal['discount']}"
                )
                last['market'].append(deal['id'])
    
    with open('last.json', 'w') as f:
        json.dump(last, f)

    channel = bot.get_channel(channelID)

    if len(embed.fields) > 0:
        await channel.send(embed = embed)

@bot.event
async def on_ready():
    mainLoop.start()

# Run bot
bot.run(os.getenv('TOKEN'))