### good practices

- while using [kubernetes](#kubernetes) you can easily clean-up unnecessary `jobs` and `pods` by running this command:

   ```commandline
   kubectl delete job <job-id-here>
   ```

  Do not delete `pvc`s or `namespace`'s unless you're sure you're want that,
  otherwise you may accidentally delete the storage used by somebody's else job.

### common errors

- install locally and remotely differnt major versions of neptune. As there is difference in `neptune.yaml` semantic
between neptune-cli v1 an v2 parse errors are rised. It may looks like:

```
  File "/usr/local/lib/python3.5/dist-packages/pykwalify/core.py", line 209, in _validate
    self._validate_sequence(value, rule, path, done=None)
  File "/usr/local/lib/python3.5/dist-packages/pykwalify/core.py", line 288, in _validate_sequence
    raise NotSequenceError(u"Value: {} is not of a sequence type".format(value))
pykwalify.errors.NotSequenceError: <NotSequenceError: error code 7: Value: {'param1': 0.985, 'param2': 1} is not of a sequence type: Path: '/'>
```
