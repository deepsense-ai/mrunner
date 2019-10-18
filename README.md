# mrunner

mrunner is a tool intended to run experiment code on different
computation systems, without manual deployment and with significantly
less configuration. Main features are:

- prepare remote environment
- deploy code
- run experiments
  - use of scheduler, based on mangement of available resources
(if remote system supports it)
- monitor experiments using [neptune](neptune.ml)

Currently [slurm](https://slurm.schedmd.com) and _(possibly)_
[kubernetes](http://kubernetes.io) clusters are supported.
It is also possible to run experiment locally.

More details may be found in _(deprecated)_ [documentation](https://deepsense-ai.github.io/mrunner)
