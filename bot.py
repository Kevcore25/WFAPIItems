import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
import os, json
import requests
from datetime import datetime, timezone
import time

prefix = '!'

bot = commands.Bot(
    command_prefix = [prefix],
    intents = discord.Intents.all()
)
load_dotenv()

# Create user dir if it doesnt exist or else it wont work
if 'users' not in os.listdir():
    os.mkdir('users')
class User:
    def __init__(self, id: int):
        self.ID = str(id)

        if self.ID+'.json' not in os.listdir('users'):
            print("Creating user")
            with open(os.path.join('users', self.ID+'.json'), 'x') as f:
                f.write('{"search": [], "inv": [], "darvo": "", "market": []}')

    def get_data(self) -> dict:
        with open(os.path.join('users', self.ID+'.json'), 'r') as f:
            return json.load(f)
        
    def set_data(self, data: dict):
        with open(os.path.join('users', self.ID+'.json'), 'w') as f:
            json.dump(data, f)

    def add_search_item(self, item: str) -> dict:
        data = self.get_data()
        # check if item already exists
        if item in data['search']:
            return {'success': False, 'reason': "Item already exists!"}
        # max 50
        if len(data['search']) >= 50:
            return {'success': False, 'reason': "A maximum of 50 items can be added!"}

        data['search'].append(item)
        self.set_data(data)

        return {'success': True}
    
    def remove_search_item(self, item: str) -> dict:
        data = self.get_data()

        # check if item already exists
        if item not in data['search']:
            return {'success': False, 'reason': "Item does not exist!"}

        data['search'].remove(item)
        self.set_data(data)

        return {'success': True}

    def append(self, key: str, value):
        data = self.get_data()
        data[key].append(value)
        self.set_data(data)

    def set_value(self, key: str, value):
        data = self.get_data()
        data[key] = value
        self.set_data(data)

@tasks.loop(seconds = 10)
async def mainLoop():
    # Get API data
    invasions: list[dict[str, str]] = requests.get("https://api.warframestat.us/pc/invasions/").json()
    darvodeals: list[dict[str, str]] = requests.get("https://api.warframestat.us/pc/dailyDeals/?language=en").json()
    marketdeals: list[dict[str, str]] = requests.get("https://api.warframestat.us/pc/flashSales/").json()

    # Iterate through every user
    for userfile in os.listdir('users'):
        with open(os.path.join('users', userfile), 'r') as f:
            userdata: dict[str, list[str]] = json.load(f)

        # Create new embed obj
        embed = discord.Embed(
            title = "Item Notification",
            color = 0x00AAFF
        )

        searchFor = userdata['search']

        def bolden(item: str):
            for keyword in searchFor:
                if keyword.lower() in item.lower():
                    return '**' + item + '**'
            else:
                return item
            
        for keyword in searchFor:
            # Invasion
            for invasion in invasions:
                dt: str = invasion['activation'].replace('Z', '+00:00')
                epoch = datetime.fromisoformat(dt).astimezone(timezone.utc).timestamp()

                # Difference must be under 0 
                difference = epoch - time.time()
                if difference <= 0:
                    # Get atker and defer
                    for stance in ('attacker', 'defender'):
                        try:
                            reward: str = invasion[stance]['reward']['asString'] # its possible to get just the rewardTypes but this is more safer
                            if keyword.lower() in reward.lower() and invasion['id'] not in userdata['inv'] and not invasion['completed']:
                                embed.add_field(
                                    name = "Invasion Alert",
                                    value = f"Attacker: {bolden(invasion['attacker']['reward']['asString'])}\nDefender: {bolden(invasion['defender']['reward']['asString'])}\nMission: {invasion['node']}"
                                )
                                userdata['inv'].append(invasion['id'])

                        except KeyError:
                            continue

            # Darvo deals
            deal = darvodeals[0]
            if keyword.lower() in deal['item'].lower() and deal['item'] != userdata['darvo']:
                userdata['darvo'] = deal['item']

                embed.add_field(
                    name = "Darvo Deal",
                    value = f"Item: **{deal['item']}**\nPrice: **{deal['salePrice']}** ~~{deal['originalPrice']}~~"
                )

            # Market Deals
            for deal in marketdeals:
                if keyword.lower() in deal['item'].lower() and deal['id'] not in userdata['market'] and not deal['expired']:
                    embed.add_field(
                        name = "Market Deal",
                        value = f"Item: **{deal['item']}**\nDiscount: {deal['discount']}"
                    )
                    userdata['market'].append(deal['id'])
            
        with open(os.path.join('users', userfile), 'w') as f:
            json.dump(userdata, f)

        # If there is any item to send...
        if len(embed.fields) > 0:
            try:
                userid = int(userfile.rstrip('.json'))

                userCtx = bot.get_user(userid)
                await userCtx.create_dm()
                await userCtx.send(embed = embed)
            except: pass


@bot.command(
    help = "Adds an item"
)
async def add(ctx, item: str):
    user = User(ctx.author.id)

    result = user.add_search_item(item)

    if result['success']:
        await ctx.send(embed=discord.Embed(
            title = "Success",
            description = f"Added `{item}` to your search list!",
            color = 0x00FF00
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title = "An error occurred",
            description = result['reason'],
            color = 0xFF0000
        ))

@bot.command(
    help = "Removes an item"
)
async def remove(ctx, item: str):
    user = User(ctx.author.id)

    result = user.remove_search_item(item)

    if result['success']:
        await ctx.send(embed=discord.Embed(
            title = "Success",
            description = f"Removed `{item}` from your search list!",
            color = 0x00FF00
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title = "An error occurred",
            description = result['reason'],
            color = 0xFF0000
        ))
        

@bot.event
async def on_ready():
    mainLoop.start()


def convPyclassToType(pytype):
    print(pytype)
    if str(pytype)[:12] == "typing.Union":
        types = str(pytype)[13:-1]
        return types.replace(", ", " or ").replace("int", "Integer").replace("float", "Decimal").replace("str", "Text").replace("bool", "True/False")
    else:
        if pytype is int: return "Integer"    
        elif pytype is float: return "Decimal"
        elif pytype is str: return "Text"
        elif pytype is bool: return "True/False"
        elif pytype is discord.member.Member: return "User"
        else: return str(pytype)[8:-2]

def formatParamsOneLine(params: dict[str, discord.ext.commands.Parameter]) -> str:
    text = []
    for p in params:
        param = params[p]
        paramType = convPyclassToType(param.converter)
        if param.required:
            text.append(f"<{param.name}: {paramType}>")
        else:
            if param.default is not None:
                text.append(f"[{param.name}: {paramType} (default {param.default})]")
            else: 
                text.append(f"[{param.name}: {paramType}]")

    return " ".join(text)

@bot.event 
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.BadArgument): #or if the command isnt found then:
        params = ctx.command.clean_params
        embed=discord.Embed(description=f"Invalid command arguments!\nCommand format:\n`{prefix}{ctx.command} {formatParamsOneLine(params)}`", color=0xff0000)
        (ctx.command).reset_cooldown(ctx)
        await ctx.send(embed=embed)
    elif isinstance(error, commands.errors.CommandNotFound): #or if the command isnt found then:
        cmd = (ctx.message.content + " ")[len(prefix):].split(" ")[0]
        if cmd.replace("!", "") != "": 
            embed=discord.Embed(description=f"`{cmd}` is not a valid command!", color=0xff0000)
            await ctx.send(embed=embed)
    elif isinstance(error, commands.errors.ConversionError): #or if the command isnt found then:
        embed=discord.Embed(description=f"A conversion error occurred! Check to see if you have the correct format for arguments.", color=0xff0000)
        (ctx.command).reset_cooldown(ctx)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title='A FATAL error occurred:', colour=0xEE0000) #Red
        embed.add_field(name='Reason:', value=str(error).replace("Command raised an exception: ", '')) 
        await ctx.send(embed=embed)
        (ctx.command).reset_cooldown(ctx)


# Run bot
bot.run(os.getenv('TOKEN'))