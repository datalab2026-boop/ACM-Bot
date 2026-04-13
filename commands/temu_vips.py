import discord
from discord import app_commands
from discord.ext import commands
import time
import datetime
import os

class TemuVipCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="temuvip", description="Exclusive information for Temu VIP members")
    async def temuvip(self, interaction: discord.Interaction):
        # Точка отсчета времени (как в ping)
        start_perf = time.perf_counter()
        
        # Проверка наличия роли "Temu VIP"
        # Бот ищет роль именно с таким названием на твоем сервере
        has_vip = discord.utils.get(interaction.user.roles, name="Temu VIP")
        
        status_text = "✨ ACTIVE" if has_vip else "❌ INACTIVE"
        color = discord.Color.gold() if has_vip else discord.Color.red()

        # Замер скорости ответа
        total_speed = round((time.perf_counter() - start_perf) * 1000)

        # Создание Embed
        embed = discord.Embed(
            title="👑 Temu VIP Status Dashboard", 
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        
        embed.add_field(
            name="User", 
            value=f"{interaction.user.mention}", 
            inline=True
        )
        
        embed.add_field(
            name="Subscription", 
            value=f"`{status_text}`", 
            inline=True
        )
        
        # Описание преимуществ
        perks = (
            "• Доступ к эксклюзивным предложениям Temu\n"
            "• Приоритетная поддержка 24/7\n"
            "• Уникальный значок в профиле"
        )
        
        embed.add_field(
            name="Temu VIP Perks", 
            value=f"```text\n{perks if has_vip else 'Purchase Temu VIP to unlock these perks!'}\n```", 
            inline=False
        )
        
        embed.set_footer(text=f"Server Sync: {total_speed}ms | PID: {os.getpid()}")

        # Ответ виден только тому, кто ввел команду (ephemeral=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    # Твой метод регистрации "Гарант" (как в ping)
    await bot.add_cog(TemuVipCommand(bot))
    try:
        await bot.add_cog(TemuVipCommand(bot))
    except discord.errors.ClientException:
        pass
        
