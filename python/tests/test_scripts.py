#!/usr/bin/env python3

import os
import sys
import unittest
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from tests.virtual_machines import create_vm, delete_vm

class TestScripts(unittest.TestCase):

    def script_execution(self, script_name, script_args):
        """
        Выполняет скрипт с указанными аргументами.
        """

        result = subprocess.run(f'python3 {script_name} {script_args}', shell=True, capture_output=True)
        if result.returncode != 0:
            self.fail(f"The script {script_name} exited with non-zero exit code: {result.stderr}")


    def test_distribute_service_scripts(self):
        """
        Тестирование скрипта распространения сервисных скриптов.
        """

        script_path = './ansible/scripts/common/distribute_service_scripts.py'
        api_gw_url = os.environ.get('API_GW_URL')
        api_gw_token = os.environ.get('API_GW_TOKEN')
        single_host = os.environ.get('SINGLE_HOST', "agent-test-scripts")
        postgresql_pass = os.environ.get('POSTGRESQL_PASS')
        version_PG = os.environ.get('VER_PG')
        try:
            create_vm(single_host, 'test_scripts')
            self.script_execution(script_path, '--help')
            self.script_execution(script_path, f'--api_gw_url {api_gw_url} --api_gw_token {api_gw_token}' 
                                            + f' --single_mode yes --single_host {single_host}' 
                                            + f' --postgresql_pass {postgresql_pass} --version_PG {version_PG}')
        except:
            delete_vm(single_host)
            self.fail('The script distribute_service_scripts.py failed.')
        finally:
            delete_vm(single_host)


if __name__ == '__main__':
    unittest.main()