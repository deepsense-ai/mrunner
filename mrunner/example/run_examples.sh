#!/usr/bin/env bash


echo "=================================================================="
echo "This script will will run examples."
echo "We assume that you have prepared env with basic setup"
echo "=================================================================="

RUN_LOCAL=FALSE
RUN_PROMETHEUS=FALSE

echo "Should we run?"
select yn in "Locally" "Prometheus" "All"; do
    case $yn in
        "Locally" ) RUN_LOCAL=TRUE;break;;
        "Prometheus" ) RUN_PROMETHEUS=TRUE;break;;
        "All" ) RUN_PROMETHEUS=TRUE;RUN_LOCAL=TRUE;break;;
    esac
done

echo "Activate mrunner virtual env."
source /tmp/example_venv/bin/activate


if $RUN_LOCAL; then
    echo "Run experiments locally"
    python3 experiment_basic.py --ex experiment_basic_conf.py
    echo "=================================================================="
    echo "Your first experiment has run successfully. Check it in neptune."
    echo "=================================================================="

fi

if $RUN_PROMETHEUS; then
    echo "Run experiments on prometheus."

    mrunner --config /tmp/mrunner_config.yaml --context plgrid_cpu run experiment_basic_conf.py
fi