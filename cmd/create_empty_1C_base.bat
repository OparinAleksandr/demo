@echo off
Set file=%~dp0\temp.txt
For /F "usebackq tokens=* delims=" %%i In ("%file%") Do Set token=%%i
Set VerName1C=8.3.20.1710
Set SrvName=localhost
Set BaseName=IIoT
Set SrvUserPswd=%token%

Set Path1C="C:\Program Files\1cv8\%VerName1C%\bin\1cv8.exe"
Set CreateIB=Srvr="%SrvName%";Ref="%BaseName%";DBMS="PostgreSQL";DBSrvr="%SrvName%";DB="%BaseName%";DBUID="postgres";DBPwd="%SrvUserPswd%";CrSQLDB="Y" /AddInList%BaseName%

:waitsql
  TaskList /FI "SERVICES EQ pgsql*" | Find /I "pg_ctl.exe"
  IF %ErrorLevel% == 0 ( 
      GOTO createbase
  ) ELSE (
    GOTO waitsql
  )
:createbase
  %Path1C% CREATEINFOBASE %CreateIB%
  del %file%
