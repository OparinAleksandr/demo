#!/usr/bin/env python3

import sys
import subprocess


def _run_ansible_playbook(playbook_name, extra_vars, 
                          playbook_path='./ansible/playbooks/create_vm/yandex'):
    """
    Запускает плейбуки.
    """

    ansible_command = f'ansible-playbook --extra-vars \"{extra_vars}\" {playbook_path}/{playbook_name} -vv'
    result = subprocess.run(ansible_command, shell=True, capture_output=True)

    return result


def create_vm(vm_name, vm_type="test_scripts"):
    """
    Создает виртуальную машину.
    """

    result = _run_ansible_playbook(
        "create_vm.yml",
        f"vm_name={vm_name} vm_type={vm_type}"
    )
    if result.returncode != 0:
        sys.exit(1)


def delete_vm(vm_name):
    """
    Удаляет виртуальную машину.
    """

    result = _run_ansible_playbook(
        f"dev_vm_state.yml",
        f"vm_name={vm_name} vm_action=delete"
    )
    if result.returncode != 0:
        sys.exit(1)