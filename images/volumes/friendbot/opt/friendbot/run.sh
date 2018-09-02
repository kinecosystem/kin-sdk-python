#!/bin/sh
set -e

envsubst < friendbot.cfg.envsubst > friendbot.cfg

# envsubst leaves windows carriage return "^M" artifacts when called by docker
# this fixes it
dos2unix friendbot.cfg

friendbot
