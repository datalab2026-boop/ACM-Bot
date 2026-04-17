import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Храним время последнего события, чтобы не спамить старыми записями
        self.last_checked_time = datetime.now(timezone.utc)
        
        self.GROUP_ID = str(config.GROUP_ID)
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {
            "x-api-key": self.CLOUD_API,
            "Content-Type": "application/json"
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
            # Использование эндпоинта v2 с корректным фильтром
            # ВАЖНО: Убедитесь, что в Dashboard выбрана операция "Read group audit logs"
            url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}/audit-log"
            params = {
                "filter": "action_type == 'member-join'",
                "max_page_size": 10
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # Если 404 или 403 — пробуем альтернативный роут (некоторые ключи требуют прямого обращения)
            if response.status_code != 200:
                alt_url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}:getAuditLog"
                response = requests.get(alt_url, headers=self.headers, params=params, timeout=10)

            if response.status_code != 200:
                # Вывод детальной ошибки для диагностики
                await self.log_error(f"API Error {response.status_code}. Проверьте, добавлен ли ID группы {self.GROUP_ID} в разрешения ключа.")
                return
            
            data = response.json().get('groupAuditLogEvents', [])
            if not data:
                return

            newest_time = self.last_checked_time

            for event in data:
                # Парсим время события
                raw_time = event.get('createTime', '').replace('Z', '+00:00')
                if not raw_time: continue
                
                event_time = datetime.fromisoformat(raw_time)

                if event_time <= self.last_checked_time:
                    continue
                
                if event_time > newest_time:
                    newest_time = event_time

                # Получаем ID пользователя
                user_res = event.get('user', '') # формат "users/123456"
                rbx_id = user_res.split('/')[-1] if user_res else None
                
                if rbx_id:
                    # Имя пользователя берем через публичный API (он всегда работает)
                    u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
                    username = u_info.get('name', 'Unknown')
                    
                    risk_data = self.perform_risk_check(rbx_id)
                    if risk_data:
                        risk_data['group_join'] = raw_time[:10]
                        await self.send_report(username, rbx_id, risk_data)
            
            self.last_checked_time = newest_time

        except Exception as e:
            await self.log_error(f"Ошибка в боте: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Публичные запросы
            u_req = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}")
            f_req = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count")
            b_req = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10")
            a_req = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar")

            if u_req.status_code != 200: return None
            
            u_info = u_req.json()
            f_info = f_req.json()
            b_info = b_req.json()
            a_info = a_req.json()

            results = {}
            
            # 1. Возраст аккаунта
            created_dt = datetime.fromisoformat(u_info['created'].replace('Z', '+00:00'))
            age_days = (datetime.now(timezone.utc) - created_dt).days
            results['age_days'] = age_days
            results['join_date'] = u_info['created'][:10]
            
            if age_days < 14:
                risk += 60
                reasons.append("Новорег (<14 дн)")
            elif age_days < 30:
                risk += 30
                reasons.append("Молодой (<1 мес)")
            
            # 2. Аватар
            assets = a_info.get('assets', [])
            ignored = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing = [str(a['id']) for a in assets if a.get('assetType', {}).get('name') not in ignored]
            
            if not clothing:
                risk += 40
                reasons.append("Аватар без одежды")
            else:
                starts = sum(1 for cid in clothing if int(cid) in self.STARTER_ASSET_IDS)
                if starts >= 2:
                    risk += 30
                    reasons.append("Стартовые вещи")

            # 3. Соц. показатели
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 3:
                risk += 40
                reasons.append("Нет друзей")
            
            badges = len(b_info.get('data', []))
            if badges < 2:
                risk += 20
                reasons.append("Мало бейджей")

            results['reasons'] = ", ".join(reasons) if reasons else "Чист"
            results['total_risk'] = min(risk, 100)
            results['clothing_list'] = ", ".join(clothing) if clothing else "Нет"
            
            return results
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(title=f"🛡️ Проверка: {username}", color=color)
        embed.add_field(name="ID", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Риск", value=f"**{risk}%**", inline=True)
        embed.add_field(name="Создан", value=f"{data['join_date']} ({data['age_days']} дн)", inline=False)
        embed.add_field(name="Причины", value=f"```fix\n{data['reasons']}```", inline=False)
        embed.set_footer(text=f"Друзей: {data['friends']} | Вещи: {data['clothing_list'][:50]}...")
        
        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
        
