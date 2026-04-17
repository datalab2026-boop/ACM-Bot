import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_checked_id = None # Будем использовать ID лога, это надежнее
        
        self.GROUP_ID = str(config.GROUP_ID)
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {
            "x-api-key": self.CLOUD_API,
            "Accept": "application/json"
        }
        
        self.REPORT_CHANNEL_ID = 1480592830870192329
        self.ERROR_CHANNEL_ID = 1480592830870192329

        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939
        ]
        
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        
        try:
            # Используем прокси-эндпоинт apis.roblox.com для доступа к v1 через Cloud Key
            # Это самый стабильный путь для ключей, которые "не видят" v2 ресурсы
            url = f"https://apis.roblox.com/groups/v1/groups/{self.GROUP_ID}/audit-log"
            params = {
                "actionType": "MemberJoined",
                "limit": 10,
                "sortOrder": "Desc"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code != 200:
                # Если всё еще 404, значит Cloud Key в принципе не имеет доступа к Audit Log
                # Попробуем вывести более детальную ошибку
                await self.log_error(f"Ошибка API {response.status_code}. Проверь, включен ли 'Read Audit Log' в ключе.")
                return
            
            data = response.json().get('data', [])
            if not data:
                return

            # Сортируем: старые в начале, новые в конце
            for entry in reversed(data):
                log_id = entry['id']
                
                if self.last_checked_id and log_id <= self.last_checked_id:
                    continue

                # В v1 данные лежат в actor.user
                user_info = entry.get('actor', {}).get('user', {})
                rbx_id = user_info.get('userId')
                username = user_info.get('username')
                
                if rbx_id:
                    risk_data = self.perform_risk_check(rbx_id)
                    if risk_data:
                        risk_data['group_join'] = entry.get('created', 'N/A')[:10]
                        await self.send_report(username, rbx_id, risk_data)
                
                self.last_checked_id = log_id

        except Exception as e:
            await self.log_error(f"Ошибка: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Эти API публичные, им ключ не нужен
            u = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            a = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            # Возраст
            created_dt = datetime.fromisoformat(u['created'].replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - created_dt).days
            
            if age < 14: 
                risk += 60
                reasons.append("Новорег (<14д)")
            elif age < 30: 
                risk += 30
                reasons.append("Молодой (<30д)")

            # Аватар
            assets = a.get('assets', [])
            clothing = [str(x['id']) for x in assets if x.get('assetType', {}).get('name') not in ['Torso', 'Head', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg']]
            
            if not clothing:
                risk += 40
                reasons.append("Голый аватар")
            else:
                is_starter = sum(1 for i in clothing if int(i) in self.STARTER_ASSET_IDS)
                if is_starter >= 2:
                    risk += 30
                    reasons.append("Стартовый скин")

            # Друзья
            friends = f.get('count', 0)
            if friends < 5:
                risk += 30
                reasons.append("Мало друзей")

            return {
                "total_risk": min(risk, 100),
                "reasons": ", ".join(reasons) if reasons else "Чист",
                "join_date": u['created'][:10],
                "age_days": age,
                "friends": friends
            }
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        color = discord.Color.red() if data['total_risk'] > 70 else discord.Color.gold() if data['total_risk'] > 30 else discord.Color.green()
        
        embed = discord.Embed(title=f"🛡️ Проверка: {username}", color=color)
        embed.add_field(name="ID", value=rbx_id, inline=True)
        embed.add_field(name="Риск", value=f"{data['total_risk']}%", inline=True)
        embed.add_field(name="Создан", value=f"{data['join_date']} ({data['age_days']} дн)", inline=False)
        embed.add_field(name="Причины", value=f"```fix\n{data['reasons']}```", inline=False)
        
        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel: await channel.send(f"❌ {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
        
