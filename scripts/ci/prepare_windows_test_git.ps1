# The live trampoline tests require a real Git-for-Windows git-core tree.
# The test environment may provide only setup-pm's pinned PortableGit on PATH.
# Stage that verified distribution only on disposable GitHub-hosted runners.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') {
    throw 'This test prerequisite may only be prepared on a disposable GitHub-hosted runner.'
}
$target = Join-Path $env:ProgramFiles 'Git'
$corePaths = @('mingw64/libexec/git-core/git.exe', 'clangarm64/libexec/git-core/git.exe', 'mingw32/libexec/git-core/git.exe')
if (-not (Test-Path -LiteralPath $target)) {
    $sourceJson = python -c 'import json, pm; p = pm.installed_package("git"); assert p is not None, "setup-pm must prepare the locked Git pin"; print(json.dumps(str(p.path)))'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the already-verified PM Git distribution.' }
    $source = $sourceJson | ConvertFrom-Json
    $sourceCores = @($corePaths | ForEach-Object { Join-Path $source $_ } | Where-Object { Test-Path -LiteralPath $_ })
    if ($sourceCores.Count -eq 0) { throw 'The locked Git distribution does not provide the required native git-core fixture.' }
    Copy-Item -LiteralPath $source -Destination $target -Recurse
}
$cores = @($corePaths | ForEach-Object { Join-Path $target $_ } | Where-Object { Test-Path -LiteralPath $_ })
if ($cores.Count -eq 0) { throw 'Existing Program Files Git does not satisfy the native test prerequisite; refusing to overwrite it.' }
foreach ($core in $cores) {
    & $core --version
    if ($LASTEXITCODE -ne 0) { throw 'The prepared native Git executable cannot run.' }
}
