#сама функция транслитерации
function Translit {
param([string]$inString)
$Translit = @{
[char]'а' = "a"
[char]'А' = "A"
[char]'б' = "b"
[char]'Б' = "B"
[char]'в' = "v"
[char]'В' = "V"
[char]'г' = "g"
[char]'Г' = "G"
[char]'д' = "d"
[char]'Д' = "D"
[char]'е' = "e"
[char]'Е' = "E"
[char]'ё' = "yo"
[char]'Ё' = "Yo"
[char]'ж' = "zh"
[char]'Ж' = "Zh"
[char]'з' = "z"
[char]'З' = "Z"
[char]'и' = "i"
[char]'И' = "I"
[char]'й' = "j"
[char]'Й' = "J"
[char]'к' = "k"
[char]'К' = "K"
[char]'л' = "l"
[char]'Л' = "L"
[char]'м' = "m"
[char]'М' = "M"
[char]'н' = "n"
[char]'Н' = "N"
[char]'о' = "o"
[char]'О' = "O"
[char]'п' = "p"
[char]'П' = "P"
[char]'р' = "r"
[char]'Р' = "R"
[char]'с' = "s"
[char]'С' = "S"
[char]'т' = "t"
[char]'Т' = "T"
[char]'у' = "u"
[char]'У' = "U"
[char]'ф' = "f"
[char]'Ф' = "F"
[char]'х' = "h"
[char]'Х' = "H"
[char]'ц' = "c"
[char]'Ц' = "C"
[char]'ч' = "ch"
[char]'Ч' = "Ch"
[char]'ш' = "sh"
[char]'Ш' = "Sh"
[char]'щ' = "sch"
[char]'Щ' = "Sch"
[char]'ъ' = ""
[char]'Ъ' = ""
[char]'ы' = "y"
[char]'Ы' = "Y"
[char]'ь' = ""
[char]'Ь' = ""
[char]'э' = "e"
[char]'Э' = "E"
[char]'ю' = "yu"
[char]'Ю' = "Yu"
[char]'я' = "ya"
[char]'Я' = "Ya"
}
$outCHR=""
foreach ($CHR in $inCHR = $inString.ToCharArray())
{
if ($Translit[$CHR] -cne $Null )
{$outCHR += $Translit[$CHR]}
else
{$outCHR += $CHR}
}
Write-Output $outCHR
}

Import-Module activedirectory
Import-Csv "C:\pss\UPL_1.csv" | ForEach-Object {
$uname = $_.LastName + " " + $_.FirstName + " " + $_.Initials
#переводим в транслит фамилию, имя и отчество
$transLastName=Translit($_.LastName)
$transFirstName=Translit($_.FirstName)
$transInitials=Translit($_.Initials)
$transuname = $transLastName + " " + $transFirstName + " " + $transInitials
$san = $transLastName + "." + $transFirstName[0] + $transInitials[0]
$upn = $san + "@doamin.local"
$defpass = $transLastName[0] + $transFirstName[0] + $transInitials[0] + "123"
New-ADUser -Name  $transuname `
-DisplayName $uname `
-GivenName $_.FirstName `
-Surname $_.LastName `
-Initials $_.Initials `
-Description $_.Description `
-UserPrincipalName $upn `
-Path $_.OU `
-SamAccountName $san `
-AccountPassword (ConvertTo-SecureString $defpass -AsPlainText -force) `
-Enabled $true `
-PasswordNeverExpires $true
}