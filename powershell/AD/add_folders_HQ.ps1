﻿#указываем путь к корневой папке
$share = "C:\public"
#берем csv файл со списком имен групп и названием папок
Import-Csv "C:\pss\list_of_folders_by_groups_HQ.csv" | ForEach-Object {