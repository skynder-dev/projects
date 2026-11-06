# Merch Forge · Data adapter boundary
# Owns HTTP transport only. Product UI must not be implemented here.
function Invoke-ForgeApi([string]$Action,[hashtable]$Payload=@{}) {
    if ([string]::IsNullOrWhiteSpace($script:OwnerKey)) { throw 'Workspace access is required.' }
    $body=@{action=$Action}; foreach($k in $Payload.Keys){$body[$k]=$Payload[$k]}; $json=ConvertTo-Json -InputObject $body -Depth 60 -Compress
    try {
        $r=Invoke-RestMethod -Uri $script:ApiUrl -Method Post -Headers @{'x-forge-token'=$script:OwnerKey} -ContentType 'application/json' -Body $json -TimeoutSec 30
        if ($null -eq $r) { throw 'EMPTY_RESPONSE: Forge API returned an empty response.' }
        if ($r.PSObject.Properties.Name -contains 'ok' -and -not $r.ok) { throw ('API_ERROR: '+[string]$r.error) }
        return $r
    } catch {
        $code=Get-HttpStatusCode $_.Exception
        $message=$_.Exception.Message; if ([string]::IsNullOrWhiteSpace($message)){$message='Forge API request failed.'}
        if ($code -eq 401) { Remove-EncryptedOwnerKey; $script:OwnerKey=$null }
        if($code -gt 0){throw ("HTTP {0}: {1}" -f $code,$message)}
        throw $message
    }
}
