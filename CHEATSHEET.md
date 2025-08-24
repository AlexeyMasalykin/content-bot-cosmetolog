# 🚀 Content Bot - Шпаргалка команд

## ⚡ Быстрые команды

### Управление сервисом
```bash
sudo systemctl status content-bot    # Статус
sudo systemctl restart content-bot   # Перезапуск
sudo systemctl stop content-bot      # Остановка
sudo systemctl start content-bot     # Запуск
```

### Логи
```bash
sudo journalctl -u content-bot -f    # Логи в реальном времени
sudo journalctl -u content-bot -n 50 # Последние 50 строк
sudo journalctl -u content-bot --since "1 hour ago" # За последний час
```

### Обновление
```bash
# Быстрый перезапуск
sudo systemctl restart content-bot

# С обновлением кода
sudo systemctl stop content-bot
git pull
source venv/bin/activate
pip install -r requirements_deploy.txt
sudo systemctl start content-bot
```

### Изменение настроек
```bash
nano .env                           # Редактировать переменные
sudo systemctl restart content-bot  # Применить изменения
```

## 🔧 Диагностика

### Проверка работы
```bash
ps aux | grep "python.*bot.py"      # Процесс бота
sudo systemctl is-active content-bot # Активен ли сервис
sudo systemctl is-enabled content-bot # Включен ли автозапуск
```

### Состояние бота
```bash
cat bot_state.json | python3 -m json.tool # Просмотр состояния
ls -la bot_state.json                      # Размер и дата изменения
```

### Ресурсы
```bash
df -h /                              # Свободное место
free -h                              # Память
top -p $(pgrep -f "python.*bot.py") # CPU и память бота
```

## 📱 Telegram команды

### Администратор
- `/admin` - стать администратором (первый раз)
- `/start_scheduler` - запустить планировщик
- Админ-панель для управления контентом

### Пользователи
- `/start` - приветствие
- `/help` - справка
- `/post` - быстрое создание поста
- `/draft` - показать текущий черновик

## 🆘 Экстренные команды

### Полная перезагрузка
```bash
sudo systemctl stop content-bot
sudo systemctl daemon-reload
sudo systemctl start content-bot
```

### Сброс состояния (ОСТОРОЖНО!)
```bash
sudo systemctl stop content-bot
cp bot_state.json bot_state_backup.json  # Бэкап
echo '{}' > bot_state.json
sudo systemctl start content-bot
```

### Откат к бэкапу
```bash
sudo systemctl stop content-bot
cp bot_state_backup.json bot_state.json
sudo systemctl start content-bot
```

---

**📖 Подробная документация: [DEPLOYMENT.md](DEPLOYMENT.md)**
