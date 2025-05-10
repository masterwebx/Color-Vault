@echo off
setlocal enabledelayedexpansion

for %%F in (*.as) do (
    echo [] > "%%F"
)

echo All .as files have been modified to contain [].
pause