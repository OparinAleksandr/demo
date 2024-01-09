#!/bin/bash

usage()
{
cat << EO

    Применение: $(basename $0)
    Запускает подключение к тестовым ВМ используя SSH и VNC
    Для подключения необходимо:
    установленный tigervncviewer
    закрытая часть ssh-ключа тестовых ВМ в файле ~/.ssh/test_vm_key
    
    Использование:
EO
  cat <<EO | column -s\& -te
    -h|--help    &помощь
    &
    Принимает ip адрес ВМ
    &
    Пример строки запуска:  &./$(basename $0) 10.135.X.X
      &
EO
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  exit 1
fi

if [[ -z $1 ]]; then
  echo -e "\n Не получен ip ВМ"
  usage
  exit 1
else
  server=$1
  
  # диапазон локальных портов
  port_down=5600
  port_up=5899

  # удаленный порт
  remote_port=5900

  #путь до закрытой части ssh-ключа
  ssh_key=$HOME/.ssh/test_vm_key

  #путь для запуска vnc_viewer
  vnc_viewer=/usr/bin/xtigervncviewer

  #пользователь на тестовой ВМ
  remote_user=yc-user

  # продолжительность ожидания подключения в сек.
  connect_timeout=5

  # ssh порт
  ssh_port=22

  # рандомизация порта подключения
  # в диапазоне от port_down до port_up
  function random_port {
    local_port=0   
    while [ "$local_port" -le $port_down ]
    do
    local_port=$RANDOM
    let "local_port %= $port_up"
    done
  }

  # проверка, что порт свободен
  random_port
  while lsof -Pi :$local_port -sTCP:LISTEN -t >/dev/null; do
    random_port
  done
  
  echo "ВНИМАНИЕ: терминал должен быть открыт на время подключения"
  echo -n "подключение в процессе: "

  # проверка доступности порта подключения по ssh
  nc -w $connect_timeout $server $ssh_port < /dev/null &> /dev/null
  if [ $? -ne 0 ];then
    echo -n " ошибка подключения"
    echo
    exit 1
  else
    # запуск ssh с пробросом порта и без записи в known_hosts
    ssh -q -i $ssh_key $remote_user@$server -NL $local_port:localhost:$remote_port -p $ssh_port -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null -o BatchMode=yes -o ConnectTimeout=$connect_timeout -o StrictHostKeyChecking=no & >/dev/null 2>&1
    # пауза на подключение
    while [ $connect_timeout -gt 0 ]
    do
      echo -n "..."
      let connect_timeout--
      sleep 1
    done
    echo
    # запуск vnc viewer на проброшенном порту
    $vnc_viewer localhost:$local_port >/dev/null 2>&1
  fi
fi