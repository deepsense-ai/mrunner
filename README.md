# mrunner

Tool for running your experiments.


## How it works. 

Currently mrunner is mostly used within [dispatcher](http://pascal-tower01.intra.codilime.com/ml-robotics/tensor-2-tensor-with-mrunner), an experiment manager tool. `mrunner` itself allows you to use the following frameworks/resources:
* run it locally with
```
mrunner/local_cli.py
```
* run it on PLGRID with
```
mrunner/plgrid_cli.py
```
* run it with Kubernetes on a remote cluster
```
mrunner/kubernetes_cli.py
```


There's an extra script 
```
command_gen_cli.py
``` 
which you can use for generating commands [True?].


## Flags

When calling `mrunner` (and also `dispatcher`) you need to provide a set of flags, some of which are obligatory. These flags depend on the resource that you are using, and some of them are inherited from Slurm or Kubernetes.  

### General `mrunner` flags: set _F_

* `--storage_url STORAGE_URL` : Path to directory where neptune CLI will store data for experiment provenance
* `--neptune` : Enable neptune for experiment
* `--tags TAGS [TAGS ...]` : Additional (to those from experiment neptune config) tags which will be added to neptune call
* `--paths_to_dump PATHS_TO_DUMP [PATHS_TO_DUMP ...]` : List of files or dirs which will be copied by neptune to storage
* `--pythonpath PYTHONPATH` : Additional paths to be added to PYTHONPATH

### `local_cli` flags 
Set _F_ plus: 

* `--config CONFIG` : Path to experiment neptune config
* `--docker_image DOCKER_IMAGE` : Docker image name to use while running experimentwithn eptune
  

### `plgrid_cli` flags
Set _F_ plus: 

* `--partition PARTITION` : Request a specific partition for the resource allocation. If not specified, the default behavior is to allow the slurm controller to select the default partition as designated by the system administrator.
* `--config CONFIG` : Path to experiment neptune config
* `--paths_to_dump_conf PATHS_TO_DUMP_CONF` : File with a list of files or dirs which will be copied by neptune to storage. [POSSIBLY redundant flag]
* `--with_yaml` : Run experiment with yaml; neptune-offline. [UNCLEAR]
* `--experiment_id EXPERIMENT_ID` 
* `--after_module_load_cmd AFTER_MODULE_LOAD_CMD` : Additional command to have, after 'module load' on PLGRID, before sourcing venv
* `--venv_path VENV_PATH` : Path to your virtual env on PLGRID
* `--cores CORES` : Number of cores to use
* `--ntasks NTASKS` : This option advises the Slurm controller that job steps run within the allocation will launch a maximum of number tasks and to provide for sufficient resources. The default is one task per node, but note that the Slurm '--cpus-per-task' option will change this default.
* `--time TIME` : Set a limit on the total run time of the job allocation. If the requested time limit exceeds the partition's time limit, the job will be left in a PENDING state (possibly indefinitely). (Used with `sbatch` flag)
* `--srun` : Run through srun command. Boolean value.
* `--sbatch` : Run through sbatch command. Boolean value. 
* `--script_name SCRIPT_NAME`: Default 'mrunner'
* `--modules_to_load MODULES_TO_LOAD` : Additional modules to load on PLGRID
* `--A A` : Charge resources used by this job to specified account. The account is an arbitrary string. The account name may be changed after job submission using the scontrol command.
* `--gres GRES` : Specifies a comma delimited list of generic consumable resources. The format of each entry on the list is 'name[[:type]:count]'; example: '--gres=gpu:2,mic=1'

### `kubernetes_cli` flags
Set _F_ plus: 

* `--nr_gpus NR_GPUS` : Number of gpus to use
* `--docker_image DOCKER_IMAGE` : Docker image name to use while running experiment with neptune
* `--node_selector_key NODE_SELECTOR_KEY` : Provide a key for Kubernetes node_selector
* `--node_selector_value NODE_SELECTOR_VALUE` : Provide a value for Kubernetes node_selector
* `--interactive` : Boolean. Use Kubernetes 'kubectl' to create 'pod', without creating 'yaml' files. Currently only 'False' is working.
* `--neptune_exp_config NEPTUNE_EXP_CONFIG` : Path to experiment neptune config. Possible change the name of the flag to "config".
* `--dry_run` : Mark True is you want have a dry-run without execution.

### `command_gen_cli` flags
Only the following flags are applicable:

* `--repeat REPEAT` : Repeat commands
* `--shuffle` : Shuffle commands
* `--limit LIMIT` : Limit number of commands






















