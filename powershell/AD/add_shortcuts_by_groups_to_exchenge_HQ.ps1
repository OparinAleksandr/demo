
#берем csv файл со списком имен групп и названием папок
Import-Csv "C:\pss\list_of_folders_by_groups_HQ.csv" | ForEach-Object {
    #путь к ярлыку
    $path = "\\dc1\hq\ou\Обмен\" + $_.folder + ".lnk"
    #путь к папке
    $target = "\\dc1\hq\ou\" + $_.folder + "\!Внешние"
    #создаём ярлык
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($path)
    $Shortcut.TargetPath = $target
    $Shortcut.Save()
}
