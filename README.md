# mrunner

- [Overview](#overview)
- [Installation](#installation)
- [Kubernetes](#kubernetes)
    - [Local kubernates tools configuration](#local-kubernates-tools-configuration)
    - [Run experiment](#run-experiment)
    - [Google Kubernetes Engine (GKE)](#google-kubernetes-engine-gke)
    - [Cluster namespaces](#cluster-namespaces)
    - [Persistent volumes](#persistent-volumes)
    - [Kubernetes tools cheat sheet](#kubernetes-tools-cheat-sheet)
- [neptune support](#neptune-support)
    - [neptune configuration](#neptune-configuration)
    - [Issues with neptune](#issues-with-neptune)
        - [kdmi server](#kdmi-server)
        - [Issue with requirements](#issue-with-requirements)
- [Remote context](#remote-context)
- [Configuration](#configuration)
- [TODO](#todo)

## Overview

mrunner is a tool intended to run experiment code on different
computation systems, without manual deployment and with significantly
less configuration. Main features are:

- prepare remote environment
- deploy code
- run experiments
  - use of scheduler, based on mangement of available resources
  (if remote system supports it)
- monitor experiments using [neptune](neptune-support)

Currently [slurm](https://slurm.schedmd.com) and
[kubernetes](http://kubernetes.io) clusters are supported.
It is also possible to run experiment locally.

## Installation

mrunner is tested on python2.7 and python3.5, but newer versions
of python3 shall also work.
Additionally we recommend to install and use mrunner in
[virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

To install it use following commands:

```shell
pip install neptune-cli==1.6
pip install git+ssh://git@pascal-tower01.intra.codilime.com/ml-robotics/mrunner.git@feature/k8s
```

Above sequence is related with neptune
[issues](#issue-with-requirements).

Also perform following configuration steps:

- [configure neptune](#neptune-configuration)
- set some [remote contexts](#remote-context) and select active one
- if you plan to use kubernetes cluster read [kubernetes](#kubernetes)
  section

## Kubernetes

Kubernetes system may be used to manage computation resources and
accordingly schedule experimentation jobs. Read more about
[Kubernetes objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/).

**Till now kubernetes support was tested only on GKE** -
thus it may need some code update in order to run on
on premise cluster.

### Local kubernates tools configuration

To manage cluster resources and jobs install
[kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl)
tool and setup local [docker](https://docs.docker.com/install/#server)
engine.

It is required to point kubectl to which cluster it needs to
communicate to. It is done by setting kubectl context, by one of
below method:

1. While using google kubernetes cluster (GKE) it is done
   with gcloud tool - see [GKE](#google-kubernetes-engine-gke) section
   for details,
1. While using [minikube](https://github.com/kubernetes/minikube)
there is created `minikube` context during starting local cluster,
1. Define context in YAML config
   TODO: add information how to define manually kubernetes clusters and
contexts.

mrunner and kubectl uses cluster defined in kubectl context. This can
be set and checked using:

```commandline
kubectl config use-context <context_name>
kubectl config current-context    # show context which is used
```

kubectl configuration is stored in `~/.kube/config` file and
can be viewed using:

```commandline
kubectl config view
```

(Need to be followed by other persons to write/check steps)

### Run experiment

Experiments are run in cluster namespace created from experiment
project name. If such namespace is missing, it is created automatically
by mrunner. See [cluster namespaces](#cluster-namespaces) section
how to switch between them. Running experiment requires as well setting
a context for mrunner. See [remote context](#remote-context) for details on how to do it.

While running experiments on kubernetes, mrunner performs following
steps:

1. Prepares docker image based on provided in command line parameters
    - see `templates/Dockerfile.jinja2` file for details
    - during build docker cache is used, so if there is no change
      in requirements.txt file, build shall be relatively fast
1. If new image was generated tags it with timestamp and push to
   docker containers repository.
1. Ensure kubernetes configuration (create resources if missing)
    - namespace named after project name exists
    - [persistent volume claim](#persistent-volumes) exists
1. Generate kubernetes job and send request to cluster

Sample command call:

```commandline
mrunner run --config neptune.yaml \
            --requirements requirements.txt  \
            --base_image python:3 experiment1.py -- --param1 1
```

Another example could be:

```commandline
mrunner --context gke.sandbox run --config $EXP_NEPTUNE_YAML \
            --base_image python:3 \
            --requirements $EXP_REQ $EXP_FILE -- \
            --epochs 3
```
Notice (in both examples) that certain flags refer to the `mrunner` itself (eg. config, base_image) and others to experiment/script
that we wish to run (eg. epochs, param1); the way these two sets are separated is relevant ('--'). Context is provided to mrunner before `run`.

### Google Kubernetes Engine (GKE)

If you plan to use [GKE](https://cloud.google.com/kubernetes-engine/)
install [gcloud](https://cloud.google.com/sdk/docs/quickstarts) tool,
which provide authorization to access GKE. It also contain functionality
to manage GKE clusters and Google Cloud Storage.

To configure cluster credentials and kubectl context follow below steps:

1. Go to [GKE console](https://console.cloud.google.com/kubernetes)
2. Select project
3. Press `connect` button on clusters list
4. Copy and paste `gcloud` command line
   - example command:
     `gcloud container clusters get-credentials cluster-1 --zone europe-west1-b --project gke-sandbox-200208`

### Cluster namespaces

For each project new namespace is created in kubernetes cluster.
This provide freedom in experiments naming, possibility to manage
resource quota per project, separate storage.
More details may be found in
[documentation](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/).

To switch kubectl to access given namespace resources by default set
kubectl context with:

```commandline
kubectl get namespace
kubectl config set-context $(kubectl config current-context) \
                           --namespace=<project_name_based_namespace>
```

Otherwise it we shall pass `--namespace|-n` option for each
`kubectl` call.

### Persistent volumes

To gather project data from different experiments in single place,
it is required to create Persistent Volume Claim.
During execution of each experiment, this volume will be mounted under
directory pointed by `$STORAGE_DIR` environment variable (the same
as configured in mrunner context). Such volume is created by mrunner,
but also it might be configured manually - especially if some specific
configuration is required. To create such volume use:

```commandline
cat <<EOF | kubectl create -f -
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: pvc.storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi    # set required volume size
EOF
```

It is required by adopted convention to name PVC with `pvc.storage`.
This step is required to be run single time per project.

### Kubernetes tools cheat sheet

To check with which cluster kubectl is communicating:

```commandline
kubectl config current-context
```

To observe from command line current status of jobs you may use

```commandline
watch 'kubectl get jobs; kubectl get pods -a'
watch 'kubectl get jobs -o wide; kubectl get pods -a -o wide'
watch 'kubectl get jobs -o wide --all-namespaces; kubectl get pods -a -o wide --field-selector=metadata.namespace!=kube-system --all-namespaces'
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

## neptune support

It is possible to run experiments with [neptune](http://neptune.ml).
In fact support is enabled by default and to disable it,
[set](configuration) `neptune` [remote context](#remote-context) config key to `false`.

### neptune configuration

mrunner reads neptune global configuration file (by default `~/.neptune.yaml`), the same
which [neptune CLI](https://docs.neptune.ml/cli/neptune/) uses. Such configuration file
can contain any of parameters keys, but most commonly we're using it to set
neptune connection and authorization parameters. Example configuration:

```yaml
host: kdmi.neptune.deepsense.io
port: 443
username: user.name@codilime.com
password: topsecret
```

More details how to configure it may be found in
[v1.6](http://neptune-docs.deepsense.codilime.com/versions/1.6/reference-guides/cli.html) and
[v2](https://docs.neptune.ml/config/intro/) documentations.

Required connection parameters are passed during remote exectution using env variables.

`neptune-cli==2` can store authrization token in `~/.neptune_tokens` but using them
is not supported by mrunner.

### Issues with neptune

#### kdmi server

Currently for "high-frequency-training" it is recommended to use
[kdmi.neptune.deepsense.io](https://kdmi.neptune.deepsense.io) server, which
it is optimized to handle such load. The problem is, that it is v1.6 neptune server,
and thus it requires `neptune-cli==1.6` (`neptune-cli==2` uses totally different server protocol;
and `neptune-cli==1.7` shall not be used).

If you don't plan to start a lot of experiments at once,
you may use [public neptune.ml](https://neptune.ml) server, which
shall work with most recent `neptune-cli` package.

#### Issue with requirements

(As on 10th Apr 18) there is issue with installation of other packages
with neptune-cli.

If put some packages with conflicting requirements, it is observed
that older version of packages are installed.
It potentially cause errors of packages which require some newer versions.

Related neptune team [jira ticket](https://codilime.atlassian.net/browse/NPT-3427)

## Remote context

To avoid passing details on configuration of computation system, it is possible
to store predefined configuration parameters. Each configuration is named and
can be selected during experiment start or set by default:

```commandline
mrunner --context plgrid.agents run foo.py -- --param1 2
mrunner run foo.py -- --param1 2    # run with context defined in current_context config key
```

To manage contexts use `context` command. Example calls:

```commandline
mrunner context
mrunner context add --name gke.sandbox --type kubernetes \
                    --registry_url https://gcr.io --storage /storage
                    --resources "tpu=1 cpu=4"
mrunner context edit gke.sandbox               # opens editor with context parameters
mrunner context delete gke.sandbox
```

Example remote contexts':

```yaml
name: gke.sandbox
type: kubernetes
registry_url: https://gcr.io
resources: cpu=4 tpu=1
neptune: true
storage: /storage
```

## Configuration

mrunner configuration may be set using `config` command. Example calls:

```commandline
mrunner config                       # show current configuration
mrunner config set <key> <value>     # set value of config key
mrunner config unset <key>           # delete config key
```

Currently available configuration keys:

- `current_context` - default context name which will be used when no other context name is provided in CLI

## Dos and don'ts

- [Kubernetes] you can easily clean-up unnecessary `jobs` and `pods` by runnign this command:
```commandline
kubectl delete pod <pod-id-here>
```
Do not delete `pvc`s unless you're sure you're want that, otherwise you may accidentally delete the storage used by somebody's else job.


## TODO

- [ ] support for GKE
- [ ] support for slurm
- [ ] dispatcher functionality (generate jobs based on specification
      in code)
- [ ] generalize support for kubernetes
  - [ ] generate kubernetes context based on mrunner remote context