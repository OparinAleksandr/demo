/**********************************************
 * выполняет копию БД источника в БД назначения
 * используя последний бэкап БД источника
 **********************************************/
-- БД источник
DECLARE @source_db nvarchar(500);
set @source_db = N'source_db_name';

-- БД назначения
DECLARE @target_db nvarchar(500);
set @target_db = N'target_db_name';

-- логическое имя файла данных БД источника
DECLARE @source_db_logical_name nvarchar(500);
SELECT @source_db_logical_name = name
FROM sys.master_files
WHERE database_id = db_id(@source_db)
  AND type = 0

-- логическое имя файла лога БД источника
DECLARE @source_db_logical_log_name nvarchar(500);
SELECT @source_db_logical_log_name = name
FROM sys.master_files
WHERE database_id = db_id(@source_db)
  AND type = 1

-- физическое имя файла данных БД назначения
DECLARE @target_db_mdf_path nvarchar(500);
SELECT @target_db_mdf_path = m.physical_name
FROM    sys.databases d
        JOIN sys.master_files m ON d.database_id = m.database_id
WHERE   
	d.name = @target_db
	AND m.[type] = 0

-- физическое имя файла лога БД назначения
DECLARE @target_db_ldf_Path nvarchar(500);
SELECT @target_db_ldf_Path = m.physical_name
FROM    sys.databases d
        JOIN sys.master_files m ON d.database_id = m.database_id
WHERE   
	d.name = @target_db
	AND m.[type] = 1

-- физическое имя файла с последним бэкапом БД источника
DECLARE @last_back_file nvarchar(500);
USE msdb; 
SELECT @last_back_file = physical_device_name 
FROM dbo.backupmediafamily 
WHERE media_set_id = (SELECT top 1 media_set_id 
                                  FROM dbo.backupset 
                                  WHERE dbo.backupset.database_name = @source_db
                                  AND dbo.backupset.type = 'D'
                                  ORDER BY backup_finish_date DESC);

-- переводим БД назначения в момнпольный режим
DECLARE @SQL_single_mode_on nvarchar(max);
SET @SQL_single_mode_on = 'ALTER DATABASE '+ @target_db +' SET SINGLE_USER WITH ROLLBACK IMMEDIATE';
exec (@SQL_single_mode_on);

-- восстанавливаем копию БД источника в БД назначения из последнего бэкапа
USE [master]
RESTORE DATABASE @target_db FROM  DISK = @last_back_file
WITH  FILE = 1,  
MOVE @source_db_logical_name TO @target_db_mdf_path,  
MOVE @source_db_logical_log_name TO @target_db_ldf_Path,  
NOUNLOAD,  REPLACE,  STATS = 5

-- логическое имя файла лога БД назначения
DECLARE @target_db_logical_log_name nvarchar(500);
SELECT @target_db_logical_log_name = name
FROM sys.master_files
WHERE database_id = db_id(@target_db)
  AND type = 1

-- переводим БД назначения в простой режим
DECLARE @SQL_simple_mode_on nvarchar(500);
set @SQL_simple_mode_on = 'ALTER DATABASE '+@target_db+' SET RECOVERY SIMPLE;'
exec (@SQL_simple_mode_on);

-- БД назначения обрезаем лог
DECLARE @SQL_shrink_log nvarchar(500);
set @SQL_shrink_log = 'USE '+@target_db+' DBCC SHRINKFILE ('+@target_db_logical_log_name+', 0, TRUNCATEONLY);'
exec (@SQL_shrink_log);

-- переводим БД назначения в режим работы
DECLARE @SQL_multi_mode_on nvarchar(max);
SET @SQL_multi_mode_on = 'ALTER DATABASE '+ @target_db +' SET MULTI_USER';
exec (@SQL_multi_mode_on);

GO