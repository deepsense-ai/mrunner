Read [presentation](http://www2.chemia.uj.edu.pl/cttc7/plgworkshop/2016.09.08.cttc7.plgrid.workshop.pdf)
from PLGrid Workshop to gain knowledge on slurm and PLGrid clusters.

### Setup slurm

### remote context keys for slurm

Possible remote context keys:

| key                  | req | description                                          | example            |
| -------------------- | --- | ---------------------------------------------------  | ------------------ |
| name                 |  R  | unique name of context which identifies him          | plgrid.plggluna.sandbox  |
| type                 |  R  | shall equal `slurm`                                  | slurm              |
| slurm_url            |  R  | username and address of slurm cluster                | chnorris@pro.cyfronet.pl    |
| storage_dir              |  R  | path to directory where neptune CLI will store data for experiment provenance (required even when neptune is disabled; may use env variables) | /storage |
| partition            |  R  | request a specific slurm partition for the resource allocation | plgrid-testing     |
| user_id              |  R  | any, meaningful user id used to identify owner of experiment | pz        |
| scratch_dir          |  O  | subdirectories under $SCRATCH dir (default `mrunner`) | mrunner            |
| resources            |  O  | defines resource limits for every experiment (by default no resource limits) | {cpu: 4, gpu: 1, mem: 8G} | 
| neptune              |  O  | enable/disable neptune (by default enabled)          | true               |
| modules_to_load      |  O  | list of space separated additional slurm modules to load  | plgrid/tools/python/3.6.0 plgrid/tools/ffmpeg/3.2.2 |
| after_module_load_ cmd | O | shell oneliner executed after slurm module load, before sourcing venv | export PATH=/net/people/plghenrykm/anaconda2/bin:$PATH; source activate opensim-rl-2.7 |
| venv                 |  O  | path to virtual environment; can be overwritten by CLI `venv` option | '/net/people/plghenrykm/ppo_tpu/ppo_env |
| time                 |  O  | Set a limit on the total run time of the job allocation. If the requested time limit exceeds the partition's time limit, the job will be left in a PENDING state (possibly indefinitely). (Used with `sbatch` flag) | 3600000 |
| ntasks               |  O  | This option advises the slurm controller that job steps run within the allocation will launch a maximum of number tasks and to provide for sufficient resources. The default is one task per node, but note that the Slurm '--cpus-per-task' option will change this default.|

### plgrid

Filesystem:
- `/net/scratch` - lustre filesystem meant for short term use (cleaned after some period of time? 1 month? number of files quota?)
    - `$SCRATCH` - your account scratch directory
    - `$SCRATCH/mrunner` - current default scratch directory for mrunner 
- `/net/archive` - lustre filesystem
    - `$PLG_GROUPS_STORAGE` - currently it points to `/net/archive/groups`
- `/net/people` - NFS filesystem
    - `$HOME` - your home directory (it is in `/net/people`)
    - 

Read [best practices](https://proteusmaster.urcf.drexel.edu/urcfwiki/index.php/Lustre_Scratch_Filesystem#Best_Practices)
while using lustre filesystem (not exactly for plgrid cluster, but certainly shall be used during)

### Run experiment on slurm

Available options specific for slurm cluster:

| key             | req | description / additional information             | example            |
| --------------- | --- | ------------------------------------------------ | ------------------ |
| config          |  R  | path to neptune experiment configuration; mrunner uses i.a. project and experiment names, parameters list | neptune.yaml |
| base_image      |  R  | name and tag of base docker image used to build experiment docker image | python:3         |
| requirements    |  R  | path to requirements.txt file with python requirements                  | requirements.txt |

Sample command call:

```commandline
mrunner run --config neptune.yaml \
            --tags "grid_search_k-12-48" --tags new_data \
            --requirements requirements.txt  \
            --base_image python:3 experiment1.py -- --param1 1
```

Another example could be:

```commandline
mrunner --context gke.sandbox run --config neptune.yaml \
                                  --base_image python:3 \
                                  --requirements requirements.txt \
                                  -- experiment1.py -- --epochs 3
```

Notice (in both examples) that certain flags refer to the `mrunner` itself
(eg. config, base_image) and others to experiment/script that we wish to run (eg. epochs, param1);
the way these two sets are separated is relevant ('--'). Context is provided to mrunner before `run`.

While running experiments on kubernetes, mrunner performs following
steps:

1. Prepares docker image based on provided in command line parameters
   - see `templates/Dockerfile.jinja2` file for details
   - during build docker cache is used, so if there is no change
in requirements.txt file, build shall be relatively fast
2. If new image was generated tags it with timestamp and published in
docker containers repository.
3. Ensure kubernetes configuration (create resources if missing)
   - namespace named after project name exists; see [cluster namespaces](#cluster-namespaces) section
how to switch `kubectl` between them.
   - [persistent volume claim](#persistent-volumes)
4. Generate kubernetes job - in fact your experiment

