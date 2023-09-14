chcp 65001

@echo off
echo ">>Запуск этого файла перезапустит 1С, но выкинет всех пользователей ИБ" &echo ">>Нажми любую кнопку, чтобы продолжить или закрой окно для отмены"

pause

echo ">>Остановка службы 1С"
net stop "1C:Enterprise 8.3 Server Agent (x86-64)"
timeout 3

echo ">>Завершение процессов"
taskkill /f /fi "IMAGENAME eq rphost*"
taskkill /f /fi "IMAGENAME eq rmngr*"
taskkill /f /fi "IMAGENAME eq ragent*"
timeout 3

echo ">>Очистка серверного кеша"
for /d %%a in ("D:\srvinfo\reg_1541\snccntx*") do rd /s /q "%%a"
timeout 3

echo ">>Запуск службы"
net start "1C:Enterprise 8.3 Server Agent (x86-64)"
timeout 3