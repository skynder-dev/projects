# New reconciliation: generation is deliberately unavailable in this package.
# This is a local capability boundary, not a worker implementation or approval.
# No settings, environment variable, provider selection or passed binding enables it.
function Get-LocalGenerationCapability {
    return [pscustomobject]@{
        available = $false
        code = 'matching_generation_worker_unavailable'
        message = 'Generation is unavailable in this package: the matching worker has not been integrated and verified. The bridge requires the v3 full-brief and dispatch-confirmation contract; the retained worker supports v2 only and does not support local FLUX. Local draft and review remain available. No generation action was performed; existing jobs and results are retained.'
    }
}
function New-LocalGenerationUnavailableError([string]$Operation='generation') {
    $capability = Get-LocalGenerationCapability
    $exception = [NotSupportedException]::new(($capability.message + ' Operation: ' + $Operation + '.'))
    $exception.Data['forge_generation_unavailable'] = $true
    $exception.Data['forge_generation_capability_code'] = 'matching_generation_worker_unavailable'
    $exception.Data['forge_generation_operation'] = $Operation
    $exception.Data['forge_worker_launch_not_attempted'] = $true
    return $exception
}
function Assert-LocalGenerationAvailable([string]$Operation='generation') {
    throw (New-LocalGenerationUnavailableError $Operation)
}
