import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Используем время для отслеживания новых событий
        self.last_checked_time = datetime.now(timezone.utc)
        
        # Данные из config.py
        self.GROUP_ID = str(config.GROUP_ID)
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.CLOUD_API}
        
        # Каналы
        self.REPORT_CHANNEL_ID = 1480592830870192329
        self.ERROR_CHANNEL_ID = 1480592830870192329

        # ID стартовых вещей для детекта пустых аккаунтов
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
            # Используем универсальный Cloud эндпоинт для логов
            url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}/audit-log"
            params = {
                "filter": "action_type == 'member-join'",
                "max_page_size": 10
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            
            if response.status_code != 200:
                # Если v2 не отвечает, пробуем v1 через прокси облака (иногда помогает при 404)
                alt_url = f"https://apis.roblox.com/groups/v1/groups/{self.GROUP_ID}/audit-log?actionType=MemberJoined&limit=5&sortOrder=Desc"
                response = requests.get(alt_url, headers=self.headers, timeout=10)
                
                if response.status_code != 200:
                    await self.log_error(f"Ошибка API ({response.status_code}): {response.text}")
                    return
                
                # Парсинг для V1 формата
                data = response.json().get('data', [])
                for entry in reversed(data):
                    log_id = entry['id']
                    # Здесь используем простую логику ID для V1
                    if hasattr(self, 'last_id') and log_id <= self.last_id: continue
                    self.last_id = log_id
                    
                    user = entry.get('actor', {}).get('user', {})
                    await self.process_user(user.get('userId'), user.get('username'), entry.get('created'))
            else:
                # Парсинг для V2 формата
                events = response.json().get('groupAuditLogEvents', [])
                newest_time = self.last_checked_time
                
                for event in events:
                    event_time = datetime.fromisoformat(event['createTime'].replace('Z', '+00:00'))
                    if event_time <= self.last_checked_time: continue
                    
                    if event_time > newest_time: newest_time = event_time
                    
                    # Извлекаем ID из строки "users/12345"
                    user_res = event.get('user', '')
                    rbx_id = user_res.split('/')[-1] if user_res else None
                    
                    if rbx_id:
                        # Получаем имя (v2 его не дает сразу)
                        u_req = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
                        await self.process_user(rbx_id, u_req.get('name', 'Unknown'), event['createTime'])
                
                self.last_checked_time = newest_time

        except Exception as e:
            await self.log_error(f"Критический сбой цикла: {str(e)}")

    async def process_user(self, rbx_id, username, join_time):
        risk_data = self.perform_risk_check(rbx_id)
        if risk_data:
            risk_data['group_join'] = join_time[:10]
            await self.send_report(username, rbx_id, risk_data)

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Сбор данных через публичные API (не требуют ключа)
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            # Проверка возраста
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14: 
                    risk += 60
                    reasons.append("Аккаунту меньше 2 недель")
                elif age_days < 31: 
                    risk += 30
                    reasons.append("Аккаунту меньше месяца")
            
            # Проверка аватара
            equipped = a_info.get('assets', [])
            ignored = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing = [str(a['id']) for a in equipped if a.get('assetType', {}).get('name') not in ignored]
            
            if not clothing:
                risk += 30
                reasons.append("Пустой аватар (нет вещей)")
                results['clothing_list'] = "Пусто"
            else:
                matches = sum(1 for item_id in clothing if int(item_id) in self.STARTER_ASSET_IDS)
                if matches >= 2:
                    risk += 35
                    reasons.append("Использует стартовые вещи")
                results['clothing_list'] = ", ".join(clothing)

            # Друзья и бейджи
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5:
                risk += 40
                reasons.append("Подозрительно мало друзей")

            badges = b_info.get('data', [])
            if len(badges) < 2:
                risk += 25
                reasons.append("Почти нет игровых бейджей")

            results['reasons'] = ", ".join(reasons) if reasons else "Подозрений нет"
            results['total_risk'] = min(risk, 100)
            return results
        except Exception:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(
            title=f"🛡️ Отчет по безопасности: {username}", 
            color=color, 
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={rbx_id}&width=420&height=420&format=png")
        
        embed.add_field(name="Пользователь", value=f"[{username}](https://www.roblox.com/users/{rbx_id}/profile)", inline=True)
        embed.add_field(name="ID", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Уровень риска", value=f"**{risk}%**", inline=True)
        
        embed.add_field(name="Дата регистрации", value=f"{data['join_date']} ({data['age_days']} дн.)", inline=True)
        embed.add_field(name="Вступил в группу", value=f"{data['group_join']}", inline=True)
        embed.add_field(name="Друзей", value=str(data.get('friends', 0)), inline=True)
        
        embed.add_field(name="Причины", value=f"```fix\n{data['reasons']}```", inline=False)
        embed.set_footer(text="Система автоматической модерации")

        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ **Ошибка мониторинга**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
    
