import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Время последней проверки (чтобы не дублировать старые входы)
        self.last_checked_time = datetime.now(timezone.utc)
        
        self.GROUP_ID = str(config.GROUP_ID)
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {
            "x-api-key": self.CLOUD_API,
            "Content-Type": "application/json"
        }
        
        # Каналы
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
            # Используем специфический путь v2 для фильтрации логов
            # Важно: В Dashboard должно быть разрешено "Read group audit logs"
            url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}:getAuditLog"
            params = {
                "filter": "action_type == 'member-join'",
                "max_page_size": 10
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # Если основной путь не сработал, пробуем стандартную коллекцию
            if response.status_code == 404:
                url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}/audit-log"
                response = requests.get(url, headers=self.headers, params=params, timeout=10)

            if response.status_code != 200:
                await self.log_error(f"Ошибка API ({response.status_code}): {response.text}")
                return
            
            data = response.json().get('groupAuditLogEvents', [])
            if not data:
                return

            newest_time = self.last_checked_time

            for event in data:
                raw_time = event.get('createTime', '').replace('Z', '+00:00')
                if not raw_time: continue
                
                event_time = datetime.fromisoformat(raw_time)

                # Пропускаем уже проверенные
                if event_time <= self.last_checked_time:
                    continue
                
                if event_time > newest_time:
                    newest_time = event_time

                # Парсим ID (формат "users/12345")
                user_res = event.get('user', '')
                rbx_id = user_res.split('/')[-1] if user_res else None
                
                if rbx_id:
                    # Имя пользователя тянем через публичный v1 (всегда работает)
                    u_req = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
                    username = u_req.get('name', f"ID:{rbx_id}")
                    
                    risk_data = self.perform_risk_check(rbx_id)
                    if risk_data:
                        risk_data['group_join'] = raw_time[:10]
                        await self.send_report(username, rbx_id, risk_data)
            
            self.last_checked_time = newest_time

        except Exception as e:
            await self.log_error(f"Сбой цикла: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Запросы к публичным API
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            # 1. Дата создания
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14:
                    risk += 60
                    reasons.append("Меньше 2 недель")
                elif age_days < 30:
                    risk += 30
                    reasons.append("Меньше месяца")

            # 2. Аватар
            assets = a_info.get('assets', [])
            ignored = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing = [str(a['id']) for a in assets if a.get('assetType', {}).get('name') not in ignored]
            
            if not clothing:
                risk += 40
                reasons.append("Пустой аватар")
            else:
                matches = sum(1 for cid in clothing if int(cid) in self.STARTER_ASSET_IDS)
                if matches >= 2:
                    risk += 30
                    reasons.append("Стартовые вещи")

            # 3. Друзья
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5:
                risk += 30
                reasons.append("Мало друзей")

            results['reasons'] = ", ".join(reasons) if reasons else "Подозрений нет"
            results['total_risk'] = min(risk, 100)
            results['clothing_list'] = ", ".join(clothing) if clothing else "N/A"
            
            return results
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(title=f"🛡️ Проверка: {username}", color=color, timestamp=datetime.now())
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={rbx_id}&width=420&height=420&format=png")
        
        embed.add_field(name="Аккаунт", value=f"[{username}](https://www.roblox.com/users/{rbx_id}/profile)", inline=True)
        embed.add_field(name="ID", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Уровень риска", value=f"**{risk}%**", inline=True)
        embed.add_field(name="Создан", value=f"{data['join_date']} ({data['age_days']} дн.)", inline=True)
        embed.add_field(name="Причины", value=f"```fix\n{data['reasons']}```", inline=False)
        
        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ **Системная ошибка**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
            
