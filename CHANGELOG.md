# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1-rc5] - 2023-10-15

LineProcessor.add_processor no longer accepts non async functions. Use `LineProcessor.add_processor(wrap_as_async(lambda x: True))` if synchronous functions need to be used as processors.

### New

 - The processors module provides processor helpers. Currently only a ProcessUntil helper is defined, which
   processes until the line meets a predicate. (Name might be changed to `process_until` for consistency.)
 - See `LineProcessingFuncBase` if you want to write processors which interact with the parent LineProcessor instance.

### Fixed

 - LineProcessor no longer skips processors if other processors are removed during processing

### Changed

 - LineProcessor.add_processor no longer wraps non async functions into async functions,
   use wrap_as_async explicitly to add non async function to add_processor

## [0.1.1-rc4] - 2023-10-11

LineProcessor.add_processor now returns the function actually added as a line processor.
Since sync functions are wrapped into an async function, you have to use this return value for
LineProcessor.remove_processor.
It is now possible to temporarily add lineprocessors with LineProcessor.temporary_processor
### Changed
 - LineProcessor.add_processor wraps non async functions into async functions, returns the 
   function added.

### New
 - LineProcessor.temporary_processor is a context manager to temporarily inject a processor using a with statement

## [0.1.1-rc3] - 2023-09-27
Allow async callbacks for lineprocessor

### Added
 - support for async lineprocessor methods

## [0.1.1-rc2] - 2023-09-27
Fix issue with hangs.

### Added
 - support an EOF exception to shut down reader

### Fixed
 - LineReader hangs at EOF of networkstream/when read() returns 0 bytes

### Changed
 - AtomicLineReader.readline now reraises the background read processes exceptions if no further lines are in the buffer
   (i.e. if readline is bound to fail because no data is available and the backgroundprocess has crashed)

## [0.1.1-rc1] - 2023-09-21
Added mkdocs documentation, allow to import classes directly from root module

### Added
 - mkdocs documentation

### Changed
 - made important classes available from root module

## [0.1.1-beta] - 2023-09-07
Added typing
### Added
 - Package is now officially py.typed
### Changed
 - Fix all flake8/mypy warnings in src
## [0.1.1-alpha] - 2023-09-05

Allow line processors to modify and annotate the processed line for subsequent processors.

### Changed
 - LineProcessor passes an object with the line to the processors.
 Processors can now modify the line or add properties to this object for subsequent processors

### Added
 - LineReader handles multibyte reads correctly with regard to logging

## [0.1.0-alpha] - 2023-08-14

Initial alpha release