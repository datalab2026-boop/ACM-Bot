import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os

class TemuVipCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="temuvips", description="Temu VIPs list")
    async def temuvip(self, interaction: discord.Interaction):
        # ЗАМЕНИ ЭТОТ ID НА СВОЙ
        ROLE_ID = 1480292974893076491
        
        role = interaction.guild.get_role(ROLE_ID)
        
        if not role:
            await interaction.response.send_message(
                f"❌ Роль с ID `{ROLE_ID}` не найдена.", 
                ephemeral=True
            )
            return

        # Собираем список участников с этой ролью
        members = role.members
        
        if not members:
            description = "В данном списке пока пусто."
        else:
            # Формируем список. Используем mention, чтобы в ембеде были кликабельные ники
            # Ограничение 40 человек, чтобы не вылезти за лимиты Discord по символам
            member_mentions = [m.mention for m in members[:40]]
            description = "\n".join(member_mentions)
            
            if len(members) > 40:
                description += f"\n\n*...и еще {len(members) - 40} участников.*"

        embed = discord.Embed(
            title=f"👑 Temu VIPs: {role.name}",
            description=description,
            color=role.color, # Цвет берется из настроек самой роли
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        embed.add_field(name="Total Temu VIPs:", value=f"**{len(members)}**", inline=True)
        embed.set_footer(text=f"Server ID: {interaction.guild.id} | PID: {os.getpid()}")

        # Отправляем сообщение всем (ephemeral=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TemuVipCommand(bot))
    
