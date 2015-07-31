#/bin/bash
set -e

pillar_data="{"\"username\":\"$USER\""}"
sudo salt-call --local --file-root=$(pwd)/vagrant/devmode/salt/roots state.highstate pillar="$pillar_data"
