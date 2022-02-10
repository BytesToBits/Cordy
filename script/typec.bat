@echo off

echo Running mypy...

python -m mypy -p cordy --cache-dir "%~dp0..\.mypy_cache" --show-tracbeback

