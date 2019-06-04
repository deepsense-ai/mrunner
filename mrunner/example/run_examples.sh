#!/usr/bin/env bash


echo "=================================================================="
echo "This script will will run examples."
echo "We assume that you have prepared env with basic setup"
echo "=================================================================="

RUN_LOCAL=FALSE
RUN_PROMETHEUS=FALSE
RUN_EAGLE=FALSE

echo "Should we run?"
select yn in "Locally" "Prometheus" "Eagle" "All"; do
    case $yn in
        "Locally" ) RUN_LOCAL=TRUE;break;;
        "Prometheus" ) RUN_PROMETHEUS=TRUE;break;;
        "Eagle" ) RUN_EAGLE=TRUE;break;;
        "All" ) RUN_PROMETHEUS=TRUE;RUN_LOCAL=TRUE;RUN_EAGLE=True;break;;
    esac
done

echo "Activate mrunner virtual env."
source /tmp/example_venv/bin/activate


if $RUN_LOCAL; then
    echo "Run experiments locally"
    set -o xtrace
    python3 experiment_basic.py --ex experiment_basic_conf.py
    python3 experiment_basic.py --ex experiment_helper_conf.py
    set +o xtrace
    echo "=================================================================="
    echo "Your first experiments have run successfully. Check them in neptune."
    echo "=================================================================="

fi

if $RUN_PROMETHEUS; then
    echo "Run experiments on prometheus."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu run experiment_helper_conf.py
    set +o xtrace
fi

if $RUN_EAGLE; then
    echo "Run experiments on eagle."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu run experiment_helper_conf.py
    set +o xtrace
fi