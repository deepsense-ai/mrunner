# mrunner

- [Overview](#overview)
- [Installation and initial setup](#installation-and-initial-setup)
  - [Remote context](#remote-context)
- [slurm](#slurm)
  - [Setup](#setup-slurm)
  - [Run experiment](#run-experiment-on-slurm)
- [Kubernetes](#kubernetes)
  - [Setup](#setup-kubernetes)
  - [Remote context keys](#remote-context-keys-for-kubernetes)
  - [Run experiment](#run-experiment-on-kubernetes)
  - [Cluster namespaces](#cluster-namespaces)
  - [Persistent volumes](#persistent-volumes)
  - [Kubernetes tools cheat sheet](#kubernetes-tools-cheat-sheet)
- [neptune support](docs/neptune.md)
- [dos and don'ts](#dos-and-don'ts)
- [Other commands (deprecated)](#other-commands-(deprecated))

## Overview

mrunner is a tool intended to run experiment code on different
computation systems, without manual deployment and with significantly
less configuration. Main features are:

- prepare remote environment
- deploy code
- run experiments
  - use of scheduler, based on mangement of available resources
(if remote system supports it)
- monitor experiments using [neptune](docs/neptune)

Currently [slurm](https://slurm.schedmd.com) and
[kubernetes](http://kubernetes.io) clusters are supported.
It is also possible to run experiment locally.

## Installation and initial setup

mrunner is tested on python2.7 and python3.5, but newer versions
of python3 shall also work.
Additionally we recommend to install and use mrunner in
[virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

1. To install it use following commands:

   ```shell
   pip install neptune-cli==1.6
   pip install git+ssh://git@pascal-tower01.intra.codilime.com/ml-robotics/mrunner.git@develop
   ```

   Above sequence is related with neptune
   [issues](#issue-with-requirements).

1. Set some [remote contexts](#remote-context) and select active one
1. Configure clients for at least one system:
   - [slurm](#slurm)
   - [kubernetes](#kubernetes)

### Remote context

To avoid passing details on configuration of computation system, it is possible
to store predefined configuration parameters. Each configuration is named and
can be selected during experiment start or set by default:

```commandline
mrunner run foo.py -- --param1 2    # run with context defined in current_context config key
mrunner --context plgrid.agents run foo.py -- --param1 2
mrunner --context plgrid.agents --config mrunner.yaml run foo.py -- --param1 2   # loads configuration from local file (instead of user configuration directory)
```

Set of keys depends on type of remote context. For description
of available keys go to proper sections (ex. [slurm](#remote-context-keys-for-slurm),
[kubernetes](#remote-context-keys-for-kubernetes)).

To manage contexts use `context` command. Example calls:

```commandline
mrunner context
mrunner context add --name gke.sandbox --backend_type kubernetes \
                    --registry_url https://gcr.io --storage /storage
                    --resources "tpu=1 cpu=4"
mrunner context edit gke.sandbox               # opens editor with context parameters
mrunner context set-active gke.sandbox
mrunner context delete gke.sandbox
mrunner context copy gke.sandbox gke.new
mrunner --config mrunner.yaml context set-active gke.sandbox
```

Example remote contexts':

```yaml
name: gke.sandbox
type: kubernetes
registry_url: https://gcr.io
resources:
  cpu: 4
  tpu: 1
neptune: true
storage: /storage
```

## slurm

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

## Kubernetes

Kubernetes system may be used to manage computation resources and
accordingly schedule experimentation jobs. Read more about
[Kubernetes objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/).

**Till now kubernetes support was tested only on GKE** -
thus it may need some code update in order to run on
on premise cluster.

### Setup kubernetes

(Need to be followed by other persons to write/check steps)

1. To manage cluster resources and jobs install
[kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl)
tool and setup local [docker](https://docs.docker.com/install/#server)
engine.
1. mrunner and kubectl uses kubectl context, which points to which
cluster we'll communicate to. This structure may be configured, by one of
below methods:
   - while using google kubernetes cluster (GKE) it is done
   with gcloud tool - see [GKE](#google-kubernetes-engine-gke) section
   for details,
   - while using [minikube](https://github.com/kubernetes/minikube)
   there is created `minikube` context during starting local cluster,
   - defining context in YAML config (TBD)

    there is possiblity to switch between already configured contexts
    using:

      ```commandline
      kubectl config use-context <context_name>
      kubectl config current-context    # show context which is used
      ```

kubectl configuration is stored in `~/.kube/config` file and
can be viewed using:

```commandline
kubectl config view
```

##### Google Kubernetes Engine (GKE)

If you plan to use [GKE](https://cloud.google.com/kubernetes-engine/)
additionally follow below steps:

1. Install [gcloud](https://cloud.google.com/sdk/docs/quickstarts) tool,
which will provide authorization to access GKE clusters. It also contain functionality
to manage GKE clusters and Google Cloud Storage (GCS).
1. Configure cluster credentials and kubectl context follow below steps:
   - Go to [GKE console](https://console.cloud.google.com/kubernetes)
   - Select project
   - Press `connect` button on clusters list
   - Copy and paste `gcloud` command line
   - Authorize google cloud sdk by obtaining token with:

    ```sh
    gcloud auth application-default login
    ```
    
### remote context keys for kubernetes

Possible remote context keys:

| key             | req | description                                      | example            |
| --------------- | --- | ------------------------------------------------ | ------------------ |
| name            |  R  | unique name of context which identifies him      | rl.sandbox         |
| type            |  R  | shall equal `kubernetes`                         | kubernetes         |
| storage         |  R  | path to directory where neptune CLI will store data for experiment provenance (required even when neptune is disabled) | /storage |
| registry_url    |  R  | url to docker image repository where built experiment images will be published (shall be available also from cluster level)              | https://gcr.io     |
| resources       |  O  | defines resource limits for every experiment (by default no resource limits) | {cpu: 4, tpu: 1, mem: 8G} |
| neptune         |  O  | enable/disable neptune (by default enabled)      | true               |
| google_project_id | O | if using GKE set this key with google project id | rl-sandbox-1234    |
| default_pvc_size  | O | size of storage created for new project (see [persistent volumes](#persistent-volumes) section; by default creates volume of size `KubernetesBackend.DEFAULT_STORAGE_PVC_SIZE`) | 100G |

### Run experiment on kubernetes

Available options specific for kubernetes cluster:

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


### Cluster namespaces

For each project, new namespace is created in kubernetes cluster.
This provide freedom in experiments naming, possibility to manage
resource quota per project, separate storage.
More details may be found in
[kubernetes documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/).

kubectl tool is required to have pointed default namespaces. Otherwise, we shall pass `--namespace|-n` option for each kubectl call. To switch kubectl to access given namespace resources by default set
kubectl context with:

```commandline
kubectl get namespace
kubectl config set-context $(kubectl config current-context) \
                           --namespace=<project_based_namespace>
```

### Persistent volumes

To gather project data from different experiments in single place,
it is required to create set of Persistent Volume related resources (see diagram below and [nfs example](https://github.com/kubernetes/examples/tree/master/staging/volumes/nfs)). During execution of each experiment, it is checked for existance and correctness of this setup. The size of `pvc/storage`defines `default_pvc_size`key from mrunner context, but if not provided volume of size`KubernetesBackend.DEFAULT_STORAGE_PVC_SIZE`(40GB) will be created.

![k8s_storage](docs/images/k8s_storage.png)

By default volume is mounted under directory pointed by path from `$STORAGE_DIR` environment variable (the same as passed in `storage` key mrunner context).

### Kubernetes tools cheat sheet

To check with which cluster kubectl is communicating:

```commandline
kubectl config current-context
```

To observe from command line current status of jobs you may use

```commandline
watch 'kubectl get all,pvc,pv -a'
watch 'kubectl get all,pvc,pv -a -o wide'
watch 'kubectl get all,pvc,pv -a --field-selector=metadata.namespace!=kube-system --all-namespaces'
```

To observe logs from given pod (also completed and failed) you may use:

```commandline
kubectl logs -f <pod_name>
```

In order to connect to running pod use:

```commandline
kubectl attach <pod_name>
```

To delete job from cluster use below command. But be aware that related
pod also will be deleted.

```commandline
kubectl delete job <job_name>
```

To show details of job or pod use:

```commandline
kubectl describe <resource_name>
```

To download data from presistent volume use:

```commandline
TBD
```

## dos and don'ts

- while using [kubernetes](#kubernetes) you can easily clean-up unnecessary `jobs` and `pods` by running this command:

   ```commandline
   kubectl delete job <job-id-here>
   ```

  Do not delete `pvc`s or `namespace`'s unless you're sure you're want that,
  otherwise you may accidentally delete the storage used by somebody's else job.

## TODO

- [ ]  support for GKE
- [ ]  support for slurm
- [ ]  dispatcher functionality (generate jobs based on specification
in code)
- [ ]  generalize support for kubernetes
      - [ ]  generate kubernetes context based on mrunner remote context
- [ ] add information how to define manually kubernetes clusters and contexts.
- [ ]  how to download data from volume in a convenient way
- [ ]  how to extend volume
- [ ]  how to backup/restore volume
