# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1-alpha] - 2023-09-05

Allow line processors to modify and annotate the processed line for subsequent processors.

### Changed
 - LineProcessor passes an object with the line to the processors.
 Processors can now modify the line or add properties to this object for subsequent processors

### Added
 - LineReader handles multibyte reads correctly with regard to logging

## [0.1.0-alpha] - 2023-08-14

Initial alpha release