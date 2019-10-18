#!/usr/bin/env bash


echo "=================================================================="
echo "This script will will run examples."
echo "We assume that you have prepared env with basic setup"
echo "=================================================================="

unset RUN_LOCAL
unset RUN_PROMETHEUS
unset RUN_EAGLE
unset RUN_PROMETHEUS_SBATCH
unset RUN_EAGLE_SBATCH


echo "Should we run?"
select yn in "Locally" "Prometheus" "Eagle" "Prometheus_sbatch" "Eagle_sbatch"; do
    case $yn in
        "Locally" ) RUN_LOCAL=TRUE;break;;
        "Prometheus" ) RUN_PROMETHEUS=TRUE;break;;
        "Eagle" ) RUN_EAGLE=TRUE;break;;
        "Prometheus_sbatch" ) RUN_PROMETHEUS_SBATCH=TRUE;break;;
        "Eagle_sbatch" ) RUN_EAGLE_SBATCH=TRUE;break;;
    esac
done

echo "Activate mrunner virtual env."
source /tmp/example_venv/bin/activate


if [ ! -z "$RUN_LOCAL" ]; then
    echo "Run experiments locally"
    set -o xtrace
    python3 experiment_basic.py --ex experiment_basic_conf.py
    python3 experiment_basic.py --ex experiment_helper_conf.py
    python3 expeirment_gin.py --ex experiment_gin.py
    mpirun python3 experiment_mpi.py --ex experiment_mpi_conf.py
    set +o xtrace
    echo "=================================================================="
    echo "Your first experiments have run successfully. Check them in neptune."
    echo "=================================================================="

fi

if [ ! -z "$RUN_PROMETHEUS" ]; then
    echo "Run experiments on prometheus."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu --cmd_type srun run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu --cmd_type srun run experiment_helper_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu --cmd_type srun run experiment_gin_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu_mpi --cmd_type srun run experiment_mpi_conf.py
    set +o xtrace
fi

if [ ! -z "$RUN_EAGLE" ]; then
    echo "Run experiments on eagle."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu --cmd_type srun run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu --cmd_type srun run experiment_helper_conf.py
    set +o xtrace
fi

if [ ! -z "$RUN_PROMETHEUS_SBATCH" ]; then
    echo "Run experiments on prometheus with sbatch."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu run experiment_helper_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu run experiment_gin_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context prometheus_cpu_mpi run experiment_mpi_conf.py

    set +o xtrace
fi

if [ ! -z "$RUN_EAGLE_SBATCH" ]; then
    echo "Run experiments on eagle with sbatch."
    set -o xtrace
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu_sbatch run experiment_basic_conf.py
    mrunner --config /tmp/mrunner_config.yaml --context eagle_cpu_sbatch run experiment_helper_conf.py
    set +o xtrace
fi