@echo off
:waitsql
  TaskList /FI "SERVICES EQ pgsql*" | Find /I "pg_ctl.exe"
  IF %ErrorLevel% == 0 ( 
      GOTO setuptoken
  ) ELSE (
    GOTO waitsql
  )

:setuptoken
  Set Path_to_Pyton=C:\Python
  %Path_to_Pyton%\python.exe "%~dp0\setup_token.py"
  
  if not defined YC_TOKEN(
      GOTO setuptoken
  )
