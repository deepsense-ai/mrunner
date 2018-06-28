# dispatcher

- [Call stack](#call-stack)
  - [standard_mrunner_main](#standard_mrunner_main)
- [How to debug](#how-to-debug)

## remarks on current state

- in neptune.yaml there are placed only tags from python spec function

### directories



## Sequence

- mrunner run with python config
  - eval spec function from python config and list of `Experiment` classes
  - generate neptune.yaml for each experiment
    - use only: project name, experiment name, parameters, tags, description
    - neptune.yaml files are generated into ....
    - for generating neptune yaml there are required only dictionary with keys: 
    project, name, parameters, [tags], [description]

## Sequence (old dispatcher)

- shell script
  - env setup (environment variables + venv activate etc)
  - python dispatcher.py
    - load list of experiments
      - special support for composite experiments
    - register experiments in omninote
    - obtain XRunConfig
      - special support for composite experiments
      - update attributes from command line
    - for each experiment
      - generate neptune yaml
        - name, project
        - parameters: name, type, required, default
      - update experiment structure parameters based on CLI arguments
        - tags
      - generate mrunner cmd
      - depends on XRunType
        - slurm: update env (PLGRID_USERNAME, MRUNNER_SCRATCH_SPACE, PLGRID_HOST)
    - optionally experiments/cmds list is shuffled and/or trimmed to size
    - run experiments
      - it executes set mrunner cmd
      - depends on mrunner backend calls are sync (slurm-srun) or async call (slurm-sbatch, k8s)
      - depends on parallel flag passed in neptune CLI
        - using sequential os.system calls if no parallel call
        - using `subprocess.Popen` executed by n threads  

### standard_mrunner_main

Required enviornment variables which determine method of setting
**parameters list** and **experiment directory**:

| key                    | values | description                                          |                       
| ---------------------- | ------ | ---------------------------------------------------  |
| MRUNNER_UNDER_NEPTUNE  | 0/1    | both are obtained from neptune                                                     |
| PMILOS_DEBUG           | 0/1    | experiment directory passed as cmd argument, parameters evaluated from python file |
| RESOURCE_DIR_PATH      | path   | experiment directory pointed by this env var, parameters evaluated from neptune yaml file   |

When experiment is started:

  - under neptune - neptune `storage_dir` and params are used
  - under `PMILOS_DEBUG` additional arguments are parsed (same as in original `dispatcher.py`)
    -  `--ex` - path to experiment describing python file from which
    function pointed by `--spec` is executed; this function shall return
    structure containing `parameters` attribute containing experiment parameters
    - `--spec` - as mentioned above: name of function which returns structure
    containing parameters list
    - `--exp_dir_path` - path to experiment directory
  - when both neptune and `MRUNNER_DEBUG` environment variable are not set
    - `--neptune` - path to neptune yaml file; paramters are obtained from `parameters`
    key and `default` values are used
    - `RESOURCE_DIR_PATH` - environment variable pointing path to experiment directory
  
     
Neptune context obtained in this function is ignored.
**Experiment dir is also often ignored**, except:
- `model_rl_experiment_loop.py` - used to set log dir (see NeptuneLogger)
- `run_kanapa_ppo.py` - used to set `env_model_path`

## How to debug

TBD