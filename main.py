import discord
import os
import asyncio
from discord.ext import commands, tasks
from web_server import keep_alive
import config
from datetime import datetime

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(
            command_prefix="!", 
            intents=intents,
            heartbeat_timeout=60.0, # Если ответа нет 60 сек, выкинет ошибку
            close_timeout=10.0
        )

    async def setup_hook(self):
        print("\n=== STARTING MODULE LOADING ===")
        path = './commands'
        if not os.path.exists(path):
            print(f"CRITICAL ERROR: Folder '{path}' not found!")
            return

        loaded_count = 0
        for filename in os.listdir(path):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    if f'commands.{filename[:-3]}' in self.extensions:
                        await self.reload_extension(f'commands.{filename[:-3]}')
                    else:
                        await self.load_extension(f'commands.{filename[:-3]}')
                    print(f"✅ Loaded extension: {filename}")
                    loaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
        
        print(f"Total modules loaded: {loaded_count}")
        
        print("=== SYNCING SLASH COMMANDS ===")
        try:
            synced = await self.tree.sync()
            print(f"✅ Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f"✅ Bot is logged in as {self.user} (ID: {self.user.id})")
        # Запускаем проверку "живучести" сокета
        if not self.connection_watchdog.is_running():
            self.connection_watchdog.start()

        channel = self.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🤖 System Restarted",
                description="The bot process has been initialized and is now active.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="`ONLINE`", inline=True)
            embed.add_field(name="Instance", value="`Render.com`", inline=True)
            try:
                await channel.send(embed=embed)
            except: pass

    @tasks.loop(minutes=5)
    async def connection_watchdog(self):
        """Проверка, не завис ли бот"""
        if self.is_closed():
            return
            
        # Если задержка (latency) слишком высокая (более 20 сек), значит поток висит
        if self.latency > 20.0:
            print(f"🚨 Critical latency detected ({self.latency}s). Forcing restart...")
            await self.close()

async def run_bot():
    """Бесконечный цикл управления процессом бота"""
    while True:
        bot = MyBot()
        try:
            print("📡 Attempting to connect to Discord Gateway...")
            # reconnect=True позволяет библиотеке самой чинить мелкие разрывы
            await bot.start(config.DISCORD_TOKEN, reconnect=True)
        except Exception as e:
            print(f"⚠️ Session interrupted: {e}")
        finally:
            print("💀 Bot session closed.")
            if not bot.is_closed():
                try:
                    await asyncio.wait_for(bot.close(), timeout=5.0)
                except:
                    pass
            
            # Уменьшил до 15 секунд, чтобы быстрее возвращался в строй
            print("⏳ Waiting 15 seconds before attempt to restart process...")
            await asyncio.sleep(15) 
            print("🔄 Restarting event loop...")

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        # Запуск Flask сервера (в отдельном потоке)
        keep_alive()
        
        # Запуск основного асинхронного цикла
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            print("Bot stopped manually (KeyboardInterrupt).")
        except Exception as e:
            print(f"FATAL EXIT: {e}")
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN not found in environment variables.")
        
