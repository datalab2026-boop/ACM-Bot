import os

# Токены
DISCORD_TOKEN = os.environ.get("Bottoken")
ROBLOX_API_KEY = os.environ.get("Apitoken")
RESTART_TOKEN = os.environ.get("Restarttoken")

# Настройки каналов и ролей
GROUP_ID = 14543769
ALLOWED_ROLE_ID = 1467991343468118170  # ID роли в Discord
LOG_CHANNEL_ID = 1467475314086117459
ERROR_CHANNEL_ID = 1480592830870192329

# Полный словарь для работы бота (оставляем все ID для корректной работы)
ROLE_IDS = {
    "Guest": 82396917,
    "member": 12884901889,
    "V-1 Novitiate": 82396916,
    "V-2 Sentinel": 82400306,
    "V-3 Guardian": 96813819,
    "V-4 Tactical Specialist": 97711705,
    "V-5 Elite Guard": 96813820,
    "V-6 Corporal": 96813823,
    "V-7 Warden": 96814459,
    "V-8 Adjudicator": 96814469,
    "V-9 Paladin": 677693012,
    "SIS - Scouting and Intelligence Staff (Low Tier)": 97711635,
    "FOS - Field Operative Staff (Low Tier)": 97711697,
    "RAS - Ranking Analysis Staff (Low Tier)": 677141025,
    "SIS - Scouting and Intelligence Staff (Middle Tier)": 678163023,
    "FOS - Field Operative Staff (Middle Tier)": 677087015,
    "RAS - Ranking Analysis Staff (Middle Tier)": 677013012,
    "SIS - Scouting and Intelligence Staff (High Tier)": 677157025,
    "FOS - Field Operative Staff (High Tier)": 676955009,
    "RAS - Ranking Analysis Staff (High Tier)": 677115023,
    "TO - Trainers Oversight (Low tier)": 97711654,
    "TO - Trainers Oversight (High tier)": 97711670,
    "VIP": 97711686,
    "Roblox developer": 708195046,
    "Division administration": 677917013,
    "[JOG] - Junior Overseeing General": 97711695,
    "[OG] - Overseeing General": 97711696,
    "[SOG] - Senior Overseeing General": 97711668,
    "[DG] - Director General": 97711706,
    "[DPK] - Director of Peacekeeping": 97711719,
    "[ECI] - Executive Chief of Intelligence": 97711725,
    "[VSDI] - Vice Supreme Director of Intelligence": 82396915,
    "[SDI] Superior Director of Intelligence": 82396914
}

# Список разрешенных ролей для команд (member и верхушка удалены)
VALID_ROLES = [
    "V-1 Novitiate", 
    "V-2 Sentinel", 
    "V-3 Guardian", 
    "V-4 Tactical Specialist", 
    "V-5 Elite Guard", 
    "V-6 Corporal", 
    "V-7 Warden", 
    "V-8 Adjudicator", 
    "V-9 Paladin",
    "SIS - Scouting and Intelligence Staff (Low Tier)",
    "FOS - Field Operative Staff (Low Tier)",
    "RAS - Ranking Analysis Staff (Low Tier)",
    "SIS - Scouting and Intelligence Staff (Middle Tier)",
    "FOS - Field Operative Staff (Middle Tier)",
    "RAS - Ranking Analysis Staff (Middle Tier)",
    "SIS - Scouting and Intelligence Staff (High Tier)",
    "FOS - Field Operative Staff (High Tier)",
    "RAS - Ranking Analysis Staff (High Tier)",
    "TO - Trainers Oversight (Low tier)",
    "TO - Trainers Oversight (High tier)",
    "VIP",
    "Roblox developer",
    "Division administration"
]
