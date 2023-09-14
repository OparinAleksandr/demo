#указываем путь к корневой папке
$share = "C:\HQ\OU"
#условная группа всех пользователей домена
$everyone = [Security.Principal.NTAccount]"Domain\Пользователи домена"
#берем csv файл со списком имен групп и названием папок
Import-Csv "C:\pss\list_of_folders_by_groups_HQ.csv" | ForEach-Object {
    #получаем имя группы из файла
    $group = [Security.Principal.NTAccount]$_.groupname
    #создаём правила доступа к папкам
    #запрет на удаление
    $rdele = New-Object Security.AccessControl.FileSystemAccessRule($group,"Delete","Deny")
    #разрешение на изменения
    $rgmod = New-Object Security.AccessControl.FileSystemAccessRule($group,"Modify","ContainerInherit,ObjectInherit","None","Allow")
	$remod = New-Object Security.AccessControl.FileSystemAccessRule($everyone,"Modify","ContainerInherit,ObjectInherit","None","Allow")
    #создаём каталог отдела и устанавливаем правила доступа
    $folder_for_group = "$share\$($_.folder)"
    md $folder_for_group
    $acl = Get-Acl $folder_for_group
    #отключаем наследование прав корневой папки с сохранением наследуемых прав
    $acl.SetAccessRuleProtection($true,$true)
    #устанавливаем свои права
    $acl.AddAccessRule($rdele) | Out-Null
    $acl.AddAccessRule($rgmod) | Out-Null
    $acl | Set-Acl $folder_for_group
    #создаём подкаталог сканер 
    $sub1 = "$share\$($_.folder)\$($_.subfolder1)"
    md $sub1
    $acl = Get-Acl $sub1
    #отключаем наследование прав корневой папки с сохранением наследуемых прав
	$acl.SetAccessRuleProtection($true,$true)
    #устанавливаем свои права
    $acl.AddAccessRule($rdele) | Out-Null
	$acl | Set-Acl $sub1
    #создаём подкаталог внешние 
    $sub2 = "$share\$($_.folder)\$($_.subfolder2)"
    md $sub2
    $acl = Get-Acl $sub2
    #отключаем наследование прав корневой папки с сохранением наследуемых прав
	$acl.SetAccessRuleProtection($true,$true)
    #устанавливаем свои права
    $acl.AddAccessRule($rdele) | Out-Null
    $acl.AddAccessRule($rgmod) | Out-Null
    $acl.AddAccessRule($remod) | Out-Null
	$acl | Set-Acl $sub2
}