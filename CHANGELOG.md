# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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