# Atomic-Lines

# Intro
A toy project, wrapping asynchronous one byte readers into a sane(?) readline semantic.
If no end of line is found the request is considered timedout, and the data is kept in the buffer,
otherwise lines are returned (without the EOL character) for further processing.

The main goal is to help wrap i.e. serial access or other apis which consume data if readline times out.

For more userfriendly documentation see https://maltevesper.github.io/atomiclines/.

# Logging configuration

Logging can be configured by pointing the environment variable `ATOMICLINES_LOG_CONFIG` to a yaml file.

```
ATOMICLINES_LOG_CONFIG=logging_configuration.yaml pytest
```

The yaml file, should contain a logging dict. Example file:

```
version: 1
disable_existing_loggers: true

formatters:
    standard:
        format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    error:
        format: "%(levelname)s <PID %(process)d:%(processName)s> %(name)s.%(funcName)s(): %(message)s"

handlers:
    console:
        class: logging.StreamHandler
        level: DEBUG
        formatter: standard
        stream: ext://sys.stdout

loggers:
    atomiclines:
        level: INFO
        handlers: [console]
        propogate: no
```

## For Developers

### Bash Completion for pytest
```
pip install argcomplete # is a dev dependency too
activate-global-python-argcomplete
```