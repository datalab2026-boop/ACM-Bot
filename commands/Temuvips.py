from config import BOT_TOKEN  # Твой импорт из конфига

# ... (код инициализации bot или client) ...

@bot.tree.command(name="temuvips", description="Show up all Temu VIPs")
async def temuvips(interaction: discord.Interaction):
    role_id = 1480292974893076491
    guild = interaction.guild
    
    # Получаем объект роли
    role = guild.get_role(role_id)

    if not role:
        await interaction.response.send_message("Ошибка: Роль не найдена.", ephemeral=True)
        return

    # Получаем список всех участников с этой ролью
    # ВАЖНО: У бота должен быть включен "Server Members Intent" в панели разработчика
    members_with_role = [member.mention for member in role.members]

    if not members_with_role:
        description_text = "Список пуст."
    else:
        # Объединяем упоминания через перенос строки для столбика
        description_text = "\n".join(members_with_role)

    # Оранжевый эмбед
    embed = discord.Embed(
        title="Temu VIPs",
        description=description_text,
        color=0xffa500  # Оранжевый цвет
    )

    await interaction.response.send_message(embed=embed)
  
