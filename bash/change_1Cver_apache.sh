#!/bin/bash

if [ -z "$1" ]; then
  echo "Необходимо передать новую версию. Например 8.3.22.1923"
  exit 1
fi

conf_files=$(find /etc/apache2/conf-enabled/ -name "*.conf")

for file in $conf_files; do
  if grep -q "LoadModule _1cws_module \"/opt/1cv8/x86_64/.*\/wsap24.so\"" "$file"; then
    sed -i.bak "s|LoadModule _1cws_module \"/opt/1cv8/x86_64/.*/wsap24.so\"|LoadModule _1cws_module \"/opt/1cv8/x86_64/$1/wsap24.so\"|g" $file
    echo "Значение в файле $file успешно заменено на $1 в директории conf-enabled"
  fi
done

conf_files=$(find /etc/apache2/conf-available/ -name "*.conf")

for file in $conf_files; do
  if grep -q "LoadModule _1cws_module \"/opt/1cv8/x86_64/.*\/wsap24.so\"" "$file"; then
    sed -i.bak "s|LoadModule _1cws_module \"/opt/1cv8/x86_64/.*/wsap24.so\"|LoadModule _1cws_module \"/opt/1cv8/x86_64/$1/wsap24.so\"|g" $file
    echo "Значение в файле $file успешно заменено на $1 в директории conf-available"
  fi
done

echo "Перезагрузка Apache"
systemctl restart apache2
