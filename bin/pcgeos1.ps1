$SdkRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
python (Join-Path $SdkRoot 'bin\sdkcli.py') @args
