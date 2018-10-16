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

