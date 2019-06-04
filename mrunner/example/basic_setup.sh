#!/usr/bin/env bash

#run as basic_setup.sh PROMETHEUS_LOGIN

set -e
export PROMETHEUS_LOGIN=$1
export GRANT_NAME=$2

function prepare_local_venv {
    ENV_DIR=/tmp/example_venv
    echo "=================================================================="
    echo "Setting up local virtual env in $ENV_DIR"
    echo "We assume python3"
    echo "=================================================================="

    rm -rf $ENV_DIR
    python3 -m venv $ENV_DIR
    source $ENV_DIR/bin/activate
    pip install -r resources/requirements_local.txt
}

function prepare_remote_venv_prometheus {
    echo "=================================================================="
    echo "Setting up remote env on PROMETHEUS in mrunner_example_env"
    echo "=================================================================="
    scp resources/requirements_remote.txt $PROMETHEUS_LOGIN@pro.cyfronet.pl:
    scp resources/setup_remote_env.sh $PROMETHEUS_LOGIN@pro.cyfronet.pl:

    ssh $PROMETHEUS_LOGIN@pro.cyfronet.pl chmod +x setup_remote_env.sh
    ssh $PROMETHEUS_LOGIN@pro.cyfronet.pl ./setup_remote_env.sh
}

function prepare_remote_venv_eagle {
    echo "=================================================================="
    echo "Setting up remote env on EAGLE in mrunner_example_env"
    echo "=================================================================="
    scp resources/requirements_remote.txt $PROMETHEUS_LOGIN@eagle.man.poznan.pl:
    scp resources/setup_remote_env.sh $PROMETHEUS_LOGIN@eagle.man.poznan.pl:

    ssh $PROMETHEUS_LOGIN@eagle.man.poznan.pl chmod +x setup_remote_env.sh
    ssh $PROMETHEUS_LOGIN@eagle.man.poznan.pl srun -p plgrid-testing ./setup_remote_env.sh
}

function prepare_mrunner_config {
    echo "=================================================================="
    echo "Preparing mrunner config in /tmp/mrunner_config.yaml"
    echo "=================================================================="

    sed "s/<username>/$PROMETHEUS_LOGIN/g" resources/prometheus_config_template.yaml > /tmp/mrunner_config_1.yaml
    sed "s/<grantname>/$GRANT_NAME/g" /tmp/mrunner_config_1.yaml > /tmp/mrunner_config.yaml

    rm /tmp/mrunner_config_1.yaml

    cat /tmp/mrunner_config.yaml

}


function prepare_envs_and_mrunner_config {
    if [ -z "$PROMETHEUS_LOGIN" ]; then echo "PROMETHEUS_LOGIN must be set. exiting";exit; fi
       prepare_local_venv
       prepare_remote_venv_prometheus
#    prepare_remote_venv_eagle
      prepare_mrunner_config
}

echo "=================================================================="
echo "This script will prepare a local virutal environment, remote virtual envrionment on prometheus and simple run config."
echo "We assume that you have locally installed python3 and access to prometheus"
echo "Please review this script before running it."

echo "=================================================================="

echo "Should we run?"
select yn in "Yes" "No"; do
    case $yn in
        "Yes" ) prepare_envs_and_mrunner_config; break;;
        "No" ) echo "exiting"; exit;;
    esac
done