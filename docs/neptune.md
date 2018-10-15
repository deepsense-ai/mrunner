mrunner run experiments with [neptune](http://neptune.ml).
Currently it is not possible to disable it.

### Authorization

Method of authorization with neptune server depends on neptune version.
For v1 credentials are stored in neptune global configuration file
(by default `~/.neptune.yaml`). Example configuration:

```yaml
host: <neptune_v1_server>
port: 443
username: <email>
password: <password>
```

For version v2 `neptune account login` command is used authorize and obtain OAuth2 tokens.
More details on configuration may be found in
[v1.6](http://neptune-docs.deepsense.codilime.com/versions/1.6/reference-guides/cli.html) and
[v2](https://docs.neptune.ml/config/intro/) documentations.

#### Internals details

Tokens are stored (again depending on neptune-cli version):

- `$HOME/.neptune_tokens/` for neptune-cli>=2.0.0,neptune-cli<=2.8.14
- `$HOME/.neptune/tokens/` for neptune-cli>=2.8.15

Required connection parameters/tokens are passed during remote execution using
environment variables or attached as file to experiment archive.

### Tags

Experiment related neptune tags may be set in 4 places:
- fixed tags shall be placed in `neptune.yaml` file as `tags` key
- fixed tags may be also placed in context  as `tags` key
- run related tags may be addtionally added with CLI `--tags` parameter
- added tags programmatically to neptune context (TODO: add sample)

```commandline
mrunner run --config neptune.yaml \
            --tags "grid_search_k-12-48" --tags new_data \
            --requirements requirements.txt  \
            --base_image python:3 experiment1.py -- --param1 1
```

### Storage

[TODO: describe difference between v1 and v2]

### Running neptune in mpirun/srun experiments

[TODO: test it]

### Requirements overwriting in older versions

There is issue with installation of other packages with neptune-cli<=2.8.8.

If put some packages with conflicting requirements, it is observed
that older version of packages may be installed if after installation of neptune-cli.