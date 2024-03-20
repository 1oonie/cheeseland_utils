import config

import discord
from discord import app_commands
from discord import ui

from typing import Union, Optional
from datetime import timedelta, datetime

GUILD_ID = 907657508292792342
GUILD = discord.Object(GUILD_ID)

PARTY_CATEGORY = 907664456232890428
NPO_CATEGORY = 907662122706686005
BUSINESS_CATEGORY = 1073650939367538688

LOG_CHANNEL = 1171567720345649202

MOIA_ROLE = 1020235190632714262

class Client(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


client = Client(intents=discord.Intents.all())


@client.event
async def on_ready():
    assert client.user is not None
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')


@client.event
async def on_message_delete(message: discord.Message):
    if message.guild is not None and message.guild.id == GUILD_ID and not message.author.bot:
        logs = message.guild.get_channel(LOG_CHANNEL)
        assert isinstance(logs, discord.TextChannel)
        assert isinstance(message.channel, (discord.TextChannel, discord.Thread))
        embed = discord.Embed(
            title='Message Deleted', description=message.content, colour=0xC24B40
        )
        embed.set_author(
            name=message.author.name, icon_url=message.author.display_avatar.url
        )

        view = ui.View()
        view.add_item(
            ui.Button(
                url=message.channel.jump_url,
                label='Deleted from #' + message.channel.name,
            )
        )
        await logs.send(embed=embed, view=view)


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.guild is not None and before.guild.id == GUILD_ID and not before.author.bot and before.content != after.content:
        logs = before.guild.get_channel(LOG_CHANNEL)
        assert isinstance(logs, discord.TextChannel)
        assert isinstance(before.channel, (discord.TextChannel, discord.Thread))
        embed = discord.Embed(title='Message Edited', colour=0xC24B40)
        embed.add_field(name='Before', value=before.content, inline=False)
        embed.add_field(name='After', value=after.content, inline=False)
        embed.set_author(
            name=before.author.name, icon_url=before.author.display_avatar.url
        )

        view = ui.View()
        view.add_item(
            ui.Button(url=before.jump_url, label='Edited in #' + before.channel.name)
        )
        await logs.send(embed=embed, view=view)

@client.event
async def on_raw_thread_delete(payload: discord.RawThreadDeleteEvent):
    if payload.guild_id == GUILD_ID:
        guild = client.get_guild(GUILD_ID)
        assert guild is not None
        logs = guild.get_channel(LOG_CHANNEL)
        assert isinstance(logs, discord.TextChannel)

        parent = guild.get_channel(payload.parent_id)
        if isinstance(parent, discord.ForumChannel):
            embed = discord.Embed(title='Forum Post Deleted', colour=0xC24B40)
            embed.set_footer(text='Check the audit logs to see who deleted the thread')

            if payload.thread is not None:
                embed.add_field(name='Name', value=payload.thread.name, inline=False)
                if payload.thread.starter_message is not None:
                    embed.add_field(name='Starter Message (from cache)', value=payload.thread.starter_message.content, inline=False)
            else:
                embed.description = f'Thread ID: {payload.thread_id}'

            view = ui.View()
            view.add_item(
                ui.Button(url=parent.jump_url, label='Deleted from in #' + parent.name)
            )

            await logs.send(embed=embed, view=view)
            


class ConfirmationView(ui.View):
    def __init__(self):
        super().__init__(timeout=180)

        self.confirmed = None

    @ui.button(label='Yes', style=discord.ButtonStyle.success)
    async def _button_yes(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @ui.button(label='No', style=discord.ButtonStyle.danger)
    async def _button_no(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


class Channel(app_commands.Group, name='channel'):
    @app_commands.command(name='create', description='Create a channel in your chosen')
    @app_commands.rename(category_id='category')
    @app_commands.choices(
        category_id=[
            app_commands.Choice(name='Party', value=0),
            app_commands.Choice(name='Non-Profit Organisation', value=1),
            app_commands.Choice(name='Business', value=2),
        ]
    )
    @app_commands.describe(
        name='The name of your channel', category_id='Which category it belongs to'
    )
    async def _create_channel(
        self, interaction: discord.Interaction, name: str, category_id: int
    ):
        guild = interaction.guild
        assert (
            guild is not None
        )  # application commands are only registered in the appropriate guild anyway

        category = guild.get_channel(
            [PARTY_CATEGORY, NPO_CATEGORY, BUSINESS_CATEGORY][category_id]
        )
        assert isinstance(category, discord.CategoryChannel)
        overwrites = (
            category.overwrites
        )  # 'inheriting' permissions from parent category
        overwrites[
            discord.Object(id=interaction.user.id)
        ] = discord.PermissionOverwrite(manage_channels=True, manage_permissions=True)

        created_channel = await guild.create_text_channel(
            name=name,
            reason=f'Invocation of \'/channel create\' by {interaction.user} ({interaction.user.id})',
            overwrites=overwrites,  # type: ignore
            category=category,
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f'Created channel {created_channel.mention} in {category.name} successfully!',
                colour=0x5A9CD6,
            )
        )

    @app_commands.command(
        name='archive', description='Archive a channel (Administrator only)'
    )
    @app_commands.describe(channel='The channel you want to archive')
    async def _archive_channel(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
        ],
    ):
        assert isinstance(interaction.user, discord.Member)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                'You are not an administrator.', ephemeral=True
            )

        guild = interaction.guild
        assert guild is not None

        archive_categories = [
            922102306755969034,
            1078220892473147394,
            1171564611615596585,
        ]

        for archive_category in archive_categories:
            category = guild.get_channel(archive_category)
            assert isinstance(category, discord.CategoryChannel)
            if len(category.channels) >= 50:
                continue

            view = ConfirmationView()
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f'Are you sure you want to archive {channel.mention}?',
                    colour=0x5A9CD6,
                ),
                view=view
            )
            await view.wait()
            if view.confirmed is None:
                return await interaction.followup.send('Timed out, cancelling.')
            elif not view.confirmed:
                return await interaction.followup.send('Action aborted.')

            await channel.edit(
                category=category,
                overwrites=category.overwrites,
                reason=f'Invocation of \'/channel archive\' by {interaction.user} ({interaction.user.id})',
            )
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f'Archived {channel.mention} successfully!',
                    colour=0x5A9CD6,
                )
            )
            break
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description='We have run out of archive space.',
                    colour=0x5A9CD6,
                )
            )

def parse_duration(s: str) -> Optional[timedelta]:
    ps = s.split()    
    d = {
        'm': 1,
        'h': 60,
        'd': 1440
    }

    t = 0
    for p in ps:
        if p[-1] in d:
            if not p[:-1].isdigit():
                return
            t += int(p[:-1]) * d[p[-1]]
        else:
            return
    
    return timedelta(minutes=t)
    


@app_commands.command(name='imprison', description='Imprison a user for a given amount of time')
@app_commands.describe(user='The user you wish to imprison', duration='Use the format {n}m {n}h {n}d. For example; 3m 10h 4h for 3 minutes, 10 hours and 4 days')
async def imprison(interaction: discord.Interaction, user: discord.Member, duration: str):
    assert isinstance(interaction.user, discord.Member)
    assert interaction.guild is not None

    if not (interaction.user.get_role(MOIA_ROLE) or interaction.user.guild_permissions.administrator):
         return await interaction.response.send_message(
            'You are neither the MOIA nor an administrator.', ephemeral=True
        )
    
    if user.guild_permissions.administrator or user.top_role > interaction.guild.me.top_role:
         return await interaction.response.send_message(
            'I cannot imprison this user because a) they are an administrator or b) they are higher than me in the role hierarchy.', ephemeral=True
        )
    
    delta = parse_duration(duration)
    if delta is None:
        return await interaction.response.send_message(
            'Invalid duration string. Use the format {n}m {n}h {n}d. For example; 3m 10h 4h for 3 minutes, 10 hours and 4 days', ephemeral=True
        )
    
    await user.timeout(delta, reason=f'Invocation of \'/imprison\' by {interaction.user} ({interaction.user.id})')
    await interaction.response.send_message(f'Sucessfully imprisoned {user.mention}, they will be released <t:{round((datetime.utcnow() + delta).timestamp())}:R>')



client.tree.add_command(Channel())
client.tree.add_command(imprison)

client.run(config.token)
