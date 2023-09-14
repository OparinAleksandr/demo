@echo off
rem work with 7zip or 7za

set zippath="C:\Program Files\7-Zip"
set source_files="X:\External_file_storage"
set source_dt="D:\dt_for_copy"
set destination_files_backup="E:\Files_backup"
set destination_dt="E:\dt_backup"
set passwd="%YC_TOKEN%"
set dd=%DATE:~0,2%
set mm=%DATE:~3,2%
set yyyy=%DATE:~6,4%
set curdate=%dd%-%mm%-%yyyy%

cd %zippath%
7z.exe a -ssw -mx0 -p%passwd% -r0 %destination_files_backup%\files_backup_%curdate% %source_files%
copy /Y %destination_files_backup%\files_backup_%curdate%.7z %destination_dt%\files_backup.7z
7z.exe  h -scrc* %destination_dt%\files_backup.7z > %destination_dt%\files_backup_check_sum.txt

7z.exe a -ssw -mx0 -aoa -p%passwd% -r0 %destination_dt%\base_backup %source_dt%
7z.exe  h -scrc* %destination_dt%\base_backup.7z > %destination_dt%\base_backup_check_sum.txt

timeout 10

Forfiles /P %destination_files_backup%  /M *.7z /D -7 /C "cmd /c del /q @path"