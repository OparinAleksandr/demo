#!/bin/bash

START_TIME=$(date +%s)

usage()
{
cat << EO

    Применение: $(basename $0)
    Запускает плейбуки ansible для создания и настройки ВМ разработки 1C в Яндекc
    
    Использование:
EO
  cat <<EO | column -s\& -te
    -h|--help    &помощь
    &
    Принимаемые значения:
      &vm_name - имя машины без указания домена
      &vm_type - тип ВМ, определяет стартуют ли службы сервера, по умолчанию 'developer' - службы не стартуют
      &
    Пример строки запуска:  &./$(basename $0) vm_name='test' vm_type='developer'
      &
EO
}

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  usage
  exit 1
fi

# default vars
vm_type='developer'

set -e
export ANSIBLE_HOST_KEY_CHECKING=false
export ACTION_WARNINGS=false
export ANY_ERRORS_FATAL=true
export ANSIBLE_STDOUT_CALLBACK=yaml

for ARGUMENT in "$@"
do
   KEY=$(echo $ARGUMENT | cut -f1 -d=)

   KEY_LENGTH=${#KEY}
   VALUE="${ARGUMENT:$KEY_LENGTH+1}"

   export "$KEY"="$VALUE"
done

if [[ -z $vm_name ]]; then
  echo -e "\n Не получены необходимые значения"
  usage
  exit 1
else
  chmod -R 770 ../../playbooks
  cd ../../playbooks
  ansible-playbook ./create_vm/yandex/create_vm.yml -e "{ vm_name: $vm_name, vm_type: developer }" -vvv
  ansible-playbook ./common/mk_inventory_files.yml -e "{ local_user: yc-user, key_path: '/home/yc-user/.ssh', key_name: 'id_rsa', inventory_path: $(pwd), alias: yandex_vm, vm_id: $vm_name, ssh_user: yc-user }" -vv
  ansible-playbook ./common/wait.yml -e "{ vm: yandex_vm }" -vv
  ansible-playbook ./common/upd.yml -e "{ vm: yandex_vm }" -vv
  ansible-playbook ./common/set-timezone.yml -e "{ vm: yandex_vm }" -vv
  ansible-playbook ./common/autoupdate_off.yml -e "{vm: yandex_vm }" -vv
  ansible-playbook ./common/earlyoom_settings.yml -e "{ vm: yandex_vm }" -vv
  ansible-playbook ./common/swap_settings.yml -e "{ vm: yandex_vm }" -vv
  ansible-playbook ./common/reboot.yml -e "{ vm: yandex_vm }" -vv
fi 


END_TIME=$(date +%s)
DIFF=$(( $END_TIME - $START_TIME ))
echo "It took $DIFF seconds"