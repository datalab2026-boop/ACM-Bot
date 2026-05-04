import discord
from discord.ext import tasks, commands
import requests
import asyncio
import config

class GroupStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Настройки
        self.GROUP_ID = config.GROUP_ID
        self.STATS_CHANNEL_ID = 1500832674955133058
        
        # Запуск цикла
        self.update_stats.start()

    def cog_unload(self):
        self.update_stats.cancel()

    @tasks.loop(minutes=3)
    async def update_stats(self):
        """Раз в 3 минуты обновляет название канала с кол-вом участников."""
        await self.bot.wait_until_ready()
        
        try:
            # Используем публичный API Roblox для получения информации о группе
            url = f"https://groups.roblox.com/v1/groups/{self.GROUP_ID}"
            
            # Выполняем запрос в отдельном потоке, чтобы не блокировать бота
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, url)
            
            if response.status_code == 200:
                data = response.json()
                member_count = data.get('memberCount', 0)
                
                # Получаем объект канала
                channel = self.bot.get_channel(self.STATS_CHANNEL_ID)
                
                if channel:
                    new_name = f"⭐┆Group Members: {member_count}"
                    
                    # Проверяем, не совпадает ли текущее имя с новым, 
                    # чтобы не тратить лимиты Discord API (Rate Limits)
                    if channel.name != new_name:
                        await channel.edit(name=new_name)
                        print(f"[Stats] Название канала обновлено: {member_count}")
                else:
                    print(f"[Error] Канал с ID {self.STATS_CHANNEL_ID} не найден.")
            else:
                print(f"[Error] Roblox API вернул ошибку: {response.status_code}")

        except Exception as e:
            print(f"[Error] Ошибка в цикле статистики: {e}")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(GroupStats(bot))
    
