import-module activedirectory
Import-Csv "C:\pss\add_users_in_group.csv" | ForEach-Object {
    $uname = $_.User
    $groupname = $_.Group
    Add-ADGroupMember -Identity $groupname -Members $uname    
    }