#!/bin/bash

if [ -z "${SSH_AGENT_PID}" ]; then
  eval $(ssh-agent)
fi

if [ -z "$(ssh-add -l | grep "$(ssh-keygen -l -f ~/.ssh/id_rsa)")" ]; then
  ssh-add ~/.ssh/id_rsa
fi

if [ -z "${OS_PASSWORD}" ]; then
  OS_PASSWORD=$(read -s -p 'OpenStack password:')
fi

pipenv run python node_up.py $@