# Atomic-Lines

A toy project, wrapping asynchronous one byte readers into a sane(?) readline semantic.
If no end of line is found the request is considered timedout, and the data is kept in the buffer,
otherwise lines are returned (without the EOL character) for further processing.

The main goal is to help wrap i.e. serial access or other apis which consume data if readline times out.

## Bash Completion for pytest
```
pip install argcomplete # is a dev dependency too
activate-global-python-argcomplete
```