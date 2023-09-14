@echo off

Set file=%~dp0\temp.txt

For /F "usebackq tokens=* delims=" %%i In ("%file%") Do Set token=%%i

Set VerName=8.3.20.1710

Set SrvUserName=USR1CV8

Set SrvUserPswd=%token:~0,6%

Set PortNumber=15

Set SrvcName="1C:Enterprise 8.3 Server Agent %VerName%"

Set BinPath="\"C:\Program Files\1cv8\%VerName%\bin\ragent.exe\" -srvc -agent -regport %PortNumber%41 -port %PortNumber%40 -range %PortNumber%60:%PortNumber%91 -debug"

Set Desctiption="1C:Enterprise 8.3 Server Agent. Ver. %VerName%"

net user %SrvUserName% %SrvUserPswd% /add

WMIC USERACCOUNT WHERE "Name='%SrvUserName%'" SET PasswordExpires=FALSE

WMIC USERACCOUNT WHERE "Name='%SrvUserName%'" SET Passwordchangeable=FALSE

copy "%~dp0\ntrights.exe" "%windir%"

cd %windir%

start ntrights.exe -u %SrvUserName% +r SeServiceLogonRight

sc create %SrvcName% BinPath= %BinPath% start= auto obj= .\%SrvUserName% password= %SrvUserPswd% displayname= %Desctiption% depend= Tcpip/Dnscache/lanmanworkstation/lanmanserver/

sc start %SrvcName%

cd "C:\Program Files\1cv8\%VerName%\bin\"
start RegMSC.cmd