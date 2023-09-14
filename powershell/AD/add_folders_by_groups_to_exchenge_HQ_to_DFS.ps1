#условная группа всех пользователей домена
$everyone = [Security.Principal.NTAccount]"Domain\Пользователи домена"
#берем csv файл со списком имен групп и названием папок
Import-Csv "C:\pss\list_of_folders_by_groups_HQ.csv" | ForEach-Object {
    #создаём каталог в ДФС на основе нашего
    #путь к прострнаству имён
    $path = "\\domain\public\Обмен\" + $_.folder
    #путь к папке
    $target = "\\domaindc1\hq\ou\" + $_.folder + "\!Внешние"
    #создаём папку в ДФС
    New-DfsnFolder -Path $path -TargetPath $target -EnableTargetFailback $true
    #даём на неё права просмотра в ДФС
    Grant-DfsnAccess -Path $path -AccountName $everyone
    #включаем видимость папки на основе этих прав
    dfsutil property sd grant $path $everyone:R Protect Replace
}