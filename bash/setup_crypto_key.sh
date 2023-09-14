#!/bin/bash

usage()
{
cat << EO

    Применение: $(basename $0)
    Установка ключей КриптоПро формата .pfx
    
    Использование:
EO
  cat <<EO | column -s\& -te
    -h|--help    &помощь
    &
    Принимаемые значения:
      &key_path - путь к директории с ключом, 
      &           по умолчанию текущая директория 
      &key_pin  - пин-код ключа
      &
    Пример строки запуска:  &./$(basename $0) key_path='~/new_key' key_pin='123'
      &
EO
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  exit 1
fi


for ARGUMENT in "$@"
do
   KEY=$(echo $ARGUMENT | cut -f1 -d=)

   KEY_LENGTH=${#KEY}
   VALUE="${ARGUMENT:$KEY_LENGTH+1}"

   export "$KEY"="$VALUE"
done

if [[ -z $key_pin ]]; then
  echo -e "\n Не получен пин-код ключа"
  usage
  exit 1
else

  if [[ -z $key_path ]]; then
    key_path="./"
  fi
  
  if test -f "$key_path/"*.pfx; then
    for sign_key in "$key_path/"*.pfx; do
        /opt/cprocsp/bin/amd64/certmgr -install -pfx -pin "$key_pin" -file "$sign_key"
    done
  else
    echo "В директории $key_path нет файлов .pfx" 
  fi

fi
