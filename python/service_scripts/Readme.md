# service_scripts

Пакет скриптов:
* **make_config.py** - создание конфигов для запуска скриптов
* **pg_backup_service.py** - обслуживание баз PosgreSQL   
* **files_backup.py** - бэкап файлов
* **s3_upload.py** - формирует архив из файла бэкапа и отправляет его на S3 в Яндекс  
* **hardware_monitoring.py** - отправка метрик в Яндекс-мониторинг по свободному ресурсу в процентах для CPU, RAM и места на дисках  
* **service_monitoring.py** - отправка метрик в Яндекс-мониторинг по активности служб из списка в конфиге  

