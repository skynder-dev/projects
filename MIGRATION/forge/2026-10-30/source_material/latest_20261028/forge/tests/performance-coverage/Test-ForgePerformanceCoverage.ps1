# Native PowerShell only. Loads actual pinned product function ASTs, not module initializers.
# This is focused headless observation/coverage-label regression, not receipt authority or WPF QA.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageRoot,
    [Parameter(Mandatory=$true)][string]$PinsPath,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory=$true)][string]$RunRoot
)
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath($PackageRoot)
$RunRoot=[IO.Path]::GetFullPath($RunRoot)
$started=[DateTime]::UtcNow.ToString('o')
function Get-TestHash([string]$Path) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
}
function Assert-TestPath([string]$Path,[bool]$Directory) {
    $item=Get-Item -LiteralPath $Path -Force
    if(($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw ('Redirected path rejected: '+$Path)}
    if([bool]$item.PSIsContainer-ne$Directory){throw ('Unexpected path type: '+$Path)}
    $cursor=if($Directory){[IO.DirectoryInfo]::new($item.FullName)}else{[IO.FileInfo]::new($item.FullName).Directory}
    while($null-ne$cursor){if(($cursor.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne0){throw ('Redirected ancestor rejected: '+$cursor.FullName)};$cursor=$cursor.Parent}
}
function Assert-True($Condition,[string]$Message){if(-not$Condition){throw $Message}}
function Assert-Equal($Expected,$Actual,[string]$Message){if($Expected-cne$Actual){throw ($Message+'; expected='+[string]$Expected+' actual='+[string]$Actual)}}
function Assert-Number([double]$Expected,$Actual,[string]$Message){if($null-eq$Actual-or[double]::IsNaN([double]$Actual)-or[double]::IsInfinity([double]$Actual)-or[math]::Abs($Expected-[double]$Actual)-gt0.000000001){throw ($Message+'; expected='+$Expected+' actual='+[string]$Actual)}}
function Test-Case([string]$Name,[scriptblock]$Body){
    try{& $Body;$script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';error=$null})}
    catch{$script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';error=$_.Exception.Message})}
}
function New-TestRow([string]$Id='A',[double]$Age=1,$Units=1.25,$Royalty=10,[string]$Currency='USD',[bool]$Verified=$true){
    return [pscustomobject]@{product_id=$Id;date=$script:FixedNow.Date.AddDays(-$Age).ToString('yyyy-MM-dd');units=$Units;royalty=$Royalty;currency=$Currency;units_amount_verified=$Verified;royalty_amount_verified=$Verified;linked=$false;linked_product_key='';synthetic_only=$true}
}
function Get-FixtureRows([string]$Name){
    foreach($r in @($script:Fixtures.$Name)){
        $verified=if($null-ne$r.PSObject.Properties['verified']){[bool]$r.verified}else{$true}
        New-TestRow -Id $r.id -Age $r.age -Units $r.units -Royalty $r.royalty -Currency $r.currency -Verified $verified
    }
}
function New-TestState($Rows){
    $concepts=@();$receipts=@()
    foreach($id in @('A','B','C')){
        $concepts += [pscustomobject]@{concept_key=('concept-'+$id);title=('SYNTHETIC '+$id);packages=@();active_acceptance=$null}
        $receipts += [pscustomobject]@{concept_key=('concept-'+$id);channel='amazon_merch';marketplace='synthetic';product_id=$id;published_at='2026-01-01T00:00:00Z';fixture_verified=$true}
    }
    return [pscustomobject]@{concepts=$concepts;publication_receipts=$receipts;sales_rows=@($Rows);sales_imports=@();synthetic_only=$true}
}
function Get-TestProduct($Insights,[string]$Id='A'){
    $found=@($Insights.products|Where-Object{$_.product_id-ceq$Id});Assert-Equal 1 $found.Count ('Exactly one product '+$Id);return $found[0]
}
function Get-TestCurrency($Metrics,[string]$Currency){
    $found=@($Metrics.royalty_currencies|Where-Object{$_.currency-ceq$Currency});Assert-Equal 1 $found.Count ('Exactly one currency '+$Currency);return $found[0]
}
function Assert-Agreement($Home,$Products){
    foreach($days in @(7,30,90)){
        $units=0.0;$unitUnknown=0;$royUnknown=0;$observed=0
        foreach($p in @($Products)){$units+=[double]$p.metrics.('sales'+$days);$unitUnknown+=[int]$p.metrics.('units_unknown'+$days);$royUnknown+=[int]$p.metrics.('royalty_unknown'+$days);$observed+=[int]$p.metrics.('observed_rows'+$days)}
        Assert-Number $units $Home.('sales'+$days) ('Aggregate/per-product units '+$days)
        Assert-Equal $unitUnknown ([int]$Home.('units_unknown'+$days)) ('Aggregate/per-product unknown units '+$days)
        Assert-Equal $royUnknown ([int]$Home.('royalty_unknown'+$days)) ('Aggregate/per-product unknown royalty '+$days)
        Assert-Equal $observed ([int]$Home.('observed_rows'+$days)) ('Aggregate/per-product observed rows '+$days)
        foreach($currency in @('USD','EUR','JPY')){
            $sum=0.0;foreach($p in @($Products)){foreach($bucket in @($p.metrics.royalty_currencies)){if($bucket.currency-ceq$currency){$sum+=[double]$bucket.('royalties'+$days)}}}
            $actual=0.0;foreach($bucket in @($Home.royalty_currencies)){if($bucket.currency-ceq$currency){$actual+=[double]$bucket.('royalties'+$days)}}
            Assert-Number $sum $actual ('Aggregate/per-product '+$currency+' '+$days)
        }
    }
}
function Assert-MetricsUnknown($Metrics,[string]$Field){
    foreach($days in @(7,30,90)){
        if($Field-ceq'units'){Assert-Number 0 $Metrics.('sales'+$days) 'Unknown units excluded';Assert-Equal 1 ([int]$Metrics.('units_unknown'+$days)) 'Unknown unit counted'}
        else{Assert-Number 0 $Metrics.('royalties'+$days) 'Unknown money excluded';Assert-Equal 1 ([int]$Metrics.('royalty_unknown'+$days)) 'Unknown royalty counted';Assert-Equal 0 @($Metrics.royalty_currencies).Count 'Unknown money not bucketed'}
    }
}
Assert-TestPath $RunRoot $true
Assert-TestPath $PackageRoot $true
if(@([IO.Directory]::GetFileSystemEntries($RunRoot)).Count-ne0){throw 'Supervisor must provide a fresh, empty, private run root.'}
if($RunRoot-eq$PackageRoot-or$RunRoot.StartsWith($PackageRoot.TrimEnd([IO.Path]::DirectorySeparatorChar)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Run root cannot be inside source package.'}
$claim=$null;$receiptStream=$null
try{
    $claim=[IO.File]::Open((Join-Path $RunRoot '.forge-performance.claim'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $identity=[Text.Encoding]::UTF8.GetBytes($RunId);$claim.Write($identity,0,$identity.Length);$claim.Flush($true)
    $receiptStream=[IO.File]::Open((Join-Path $RunRoot 'receipt.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $script:Cases=New-Object Collections.Generic.List[object]
    $loaded=New-Object Collections.Generic.List[object]
    $sourceBefore=[ordered]@{};$sourceAfter=[ordered]@{};$failure=$null;$unsupportedRuntime=$false;$dateKindAvailable=$false
    $testHash=Get-TestHash $PSCommandPath;$pinsHash=Get-TestHash $PinsPath
    $fixturePath=Join-Path $PSScriptRoot 'PerformanceCoverageFixtures.json';$dependenciesPath=Join-Path $PSScriptRoot 'PerformanceCoverageDependencies.json'
    $fixtureHash=Get-TestHash $fixturePath;$dependencyHash=Get-TestHash $dependenciesPath
    $preservedPath=Join-Path $RunRoot 'existing-synthetic-fixture.txt'
    [IO.File]::WriteAllText($preservedPath,'SYNTHETIC PRESERVATION SENTINEL - no existing fixture or original may be modified.',[Text.UTF8Encoding]::new($false))
    $preservedHash=Get-TestHash $preservedPath
    try{
        $jsonCommand=Get-Command 'Microsoft.PowerShell.Utility\ConvertFrom-Json' -ErrorAction SilentlyContinue
        $dateKindAvailable=($null-ne$jsonCommand-and$jsonCommand.Parameters.ContainsKey('DateKind'))
        $versionText=$PSVersionTable.PSVersion.ToString()
        if($PSVersionTable.PSEdition-cne'Core'-or$versionText-notmatch'^\d+\.\d+(?:\.\d+){0,2}$'-or$PSVersionTable.PSVersion.Major-lt7-or($PSVersionTable.PSVersion.Major-eq7-and$PSVersionTable.PSVersion.Minor-lt5)-or!$dateKindAvailable){$unsupportedRuntime=$true;throw 'Unsupported native host: PowerShell Core 7.5+ with explicit DateKind String is required.'}
        $pins=[IO.File]::ReadAllText($PinsPath)|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        Assert-Equal 'forge.performance.coverage_pins.v1' $pins.schema 'Pinned source schema'
        Assert-Equal $testHash $pins.tests.'Test-ForgePerformanceCoverage.ps1' 'Pinned test hash'
        Assert-Equal $fixtureHash $pins.tests.'PerformanceCoverageFixtures.json' 'Pinned fixture hash'
        Assert-Equal $dependencyHash $pins.tests.'PerformanceCoverageDependencies.json' 'Pinned dependency hash'
        $dependencies=[IO.File]::ReadAllText($dependenciesPath)|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        foreach($source in $dependencies.functions.PSObject.Properties){
            $path=Join-Path $PackageRoot $source.Name;Assert-TestPath $path $false
            $hash=Get-TestHash $path;$sourceBefore[$source.Name]=$hash
            Assert-Equal $hash $pins.sources.($source.Name) ('Pinned source '+$source.Name)
            $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
            Assert-Equal 0 @($errors).Count ('Native parser errors in '+$source.Name)
            foreach($name in @($source.Value)){
                $matches=@($ast.FindAll({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and$node.Name-ceq$name},$true))
                Assert-Equal 1 $matches.Count ('Exactly one actual function '+$name)
                . ([scriptblock]::Create($matches[0].Extent.Text))
                $loaded.Add([pscustomobject]@{name=$name;source=$source.Name;start_line=$matches[0].Extent.StartLineNumber;end_line=$matches[0].Extent.EndLineNumber})
            }
        }
        $fixtureJson=[IO.File]::ReadAllText($fixturePath)
        $script:Fixtures=$fixtureJson|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        $script:FixedNow=[DateTime]::Parse($script:Fixtures.now_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
        Assert-Equal ([DateTimeKind]::Utc) $script:FixedNow.Kind 'Fixed clock must be UTC'
        $script:UiText=@{en=@{};ru=@{};es=@{}};$script:Locale='en';$script:SupportedLocales=@('en','ru','es');$script:StaticUiTranslations=@{}
        Register-PipelineUiText
        # Explicit synthetic boundary doubles. Production aggregation is never replaced.
        function Test-LocalPublicationReceiptAuthority($State,$Receipt){return ($null-ne$Receipt-and$Receipt.fixture_verified-is[bool]-and$Receipt.fixture_verified)}
        function Read-LocalCoreState {return $script:CurrentFixtureState}
        function Get-LocalAmazonPrintProfile {return $null}
        foreach($command in @('Write-LocalCoreState','Start-LocalGenerationWorker','Invoke-ForgeLocalFlux','Start-Process','Invoke-WebRequest','Invoke-RestMethod','Invoke-Expression','Remove-Item','Copy-Item','Move-Item','Set-Content','Out-File','Add-Type')){
            Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("throw 'Unexpected external or mutation boundary: $command'"))
        }
        Test-Case 'unlinked_recent_row_cannot_establish_recency' {
            $state=New-TestState @((New-TestRow -Id 'UNKNOWN' -Age 0))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'nodata'}).Count 'No dated linked transactions available'
            Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'nosales'}).Count 'Never a definitive no-sales claim'
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'A'}).Count 'A is unobserved with unknown coverage'
        }
        Test-Case 'recent_other_product_cannot_prove_zero' {
            $state=New-TestState @((New-TestRow -Id 'B' -Age 0))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'A'}).Count 'Other product activity does not prove A has zero sales'
            Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'B'}).Count 'Observed B is not called absent'
        }
        Test-Case 'unlinked_recent_row_does_not_hide_stale_linked_data' {
            $state=New-TestState @((New-TestRow -Id 'A' -Age 20),(New-TestRow -Id 'UNKNOWN' -Age 0))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            $stale=@($ins.attention|Where-Object{$_.kind-ceq'stale'})
            Assert-Equal 1 $stale.Count 'Stale linked data remains visible'
            Assert-Equal $script:FixedNow.Date.AddDays(-20).ToString('yyyy-MM-dd') $stale[0].args[0] 'Recency uses linked data only'
        }
        Test-Case 'net_zero_and_refund_rows_are_observed' {
            $state=New-TestState @((New-TestRow -Id 'A' -Units 1 -Royalty 10),(New-TestRow -Id 'A' -Units -1 -Royalty -10),(New-TestRow -Id 'B' -Units -1 -Royalty -5))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Number 0 (Get-TestProduct $ins 'A').metrics.sales30 'Net zero retained'
            Assert-Equal 2 (Get-TestProduct $ins 'A').metrics.observed_rows30 'Offsetting rows remain observed'
            foreach($id in @('A','B')){Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq$id}).Count ('Observed refund/netzero product '+$id)}
        }
        Test-Case 'unknown_amount_row_is_not_a_zero_claim' {
            $state=New-TestState @((New-TestRow -Id 'A' -Units 99 -Royalty 999 -Verified $false))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow;$p=Get-TestProduct $ins
            Assert-Equal 1 $p.metrics.units_unknown30 'Amount remains unknown'
            Assert-Equal 1 $p.metrics.observed_rows30 'The linked dated transaction was observed'
            Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'A'}).Count 'Unknown is not zero/no-transactions'
        }
        Test-Case 'thirty_day_boundary_uses_observations_not_totals' {
            $state=New-TestState @((New-TestRow -Id 'A' -Age 30),(New-TestRow -Id 'B' -Age 29 -Units 0 -Royalty 0))
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'A'}).Count 'Day30 is outside30-day observations'
            Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'-and$_.args[1]-ceq'B'}).Count 'Day29 zero transaction remains an observation'
        }
        Test-Case 'future_and_invalid_date_shapes_do_not_establish_recency' {
            $future=New-TestRow -Id 'A' -Age -1;$array=New-TestRow -Id 'B';$array.date=@($array.date)
            $state=New-TestState @($future,$array);$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 1 (Get-TestProduct $ins 'A').metrics.future_rows 'Future row excluded'
            Assert-Equal 1 (Get-TestProduct $ins 'B').metrics.undated_rows 'Singleton date array rejected'
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'nodata'}).Count 'Neither row establishes dated linked recency'
        }
        Test-Case 'newly_published_products_do_not_get_thirty_day_absence_claim' {
            $state=New-TestState @();foreach($receipt in $state.publication_receipts){$receipt.published_at=$script:FixedNow.AddDays(-5).ToString('o')}
            $ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 0 @($ins.attention|Where-Object{$_.kind-ceq'unobserved'}).Count 'Publication is younger than claimed interval'
            Assert-Equal 1 @($ins.attention|Where-Object{$_.kind-ceq'nodata'}).Count 'Coverage remains explicitly unknown'
        }
        Test-Case 'coverage_insights_do_not_mutate_input_rows' {
            $state=New-TestState @((New-TestRow -Id 'A' -Units 0 -Royalty 0),(New-TestRow -Id 'UNKNOWN' -Age 0));Reconcile-LocalSalesLinks $state
            $before=$state|ConvertTo-Json -Depth 20 -Compress
            $null=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal $before ($state|ConvertTo-Json -Depth 20 -Compress) 'Read-only coverage preserves reconciled synthetic state'
        }
        # Clock-only adapter calls the actual function with the fixed fixture UTC.
        $script:ActualInsights=(Get-Command Get-ForgePerformanceInsights -CommandType Function).ScriptBlock
        function Get-ForgePerformanceInsights($State,[datetime]$NowUtc=$script:FixedNow){& $script:ActualInsights $State $NowUtc}
        foreach($name in @('HomeMetricAttentionValue','HomeMetricPublishedValue','HomeMetricPublishedHint','HomeMetricSalesValue','HomeMetricSalesHint','HomeMetricRoyaltiesValue','HomeMetricRoyaltiesHint','HomeMetricAttentionHint')){Set-Variable -Name $name -Value $null}
        foreach($locale in @('en','ru','es')){
            $currentLocale=$locale
            Test-Case ('render_'+$locale+'_coverage_unknown') {
                $script:Locale=$currentLocale;$script:CurrentFixtureState=New-TestState @((New-TestRow -Id 'UNKNOWN' -Age 0))
                $PerformanceLeadersText=[pscustomobject]@{Text=''};$PerformanceAttentionText=[pscustomobject]@{Text=''}
                Update-PerformanceInsightsSurface
                $expected=@{en='coverage is unknown';ru='полнота данных неизвестна';es='la cobertura es desconocida'}
                Assert-True $PerformanceAttentionText.Text.Contains($expected[$currentLocale]) 'Actual renderer uses localized unknown-coverage wording'
                $forbidden=@{en='No sales for 30 days';ru='Нет продаж 30 дней';es='Sin ventas en 30 días'}
                Assert-True (-not$PerformanceAttentionText.Text.Contains($forbidden[$currentLocale])) 'Actual renderer does not assert zero sales'
            }
        }
        $script:Locale='en';Set-Item -Path Function:Get-ForgePerformanceInsights -Value $script:ActualInsights
    } catch {$failure=$_.Exception.Message}
    finally{
        try{
            foreach($source in $pins.sources.PSObject.Properties){$sourceAfter[$source.Name]=Get-TestHash (Join-Path $PackageRoot $source.Name)}
            if($sourceBefore.Count-ne$sourceAfter.Count){throw 'Source count changed during native execution.'};foreach($key in $sourceBefore.Keys){if($sourceBefore[$key]-cne$sourceAfter[$key]){throw ('Source copy changed during native execution: '+$key)}}
            if((Get-TestHash $PSCommandPath)-cne$testHash-or(Get-TestHash $PinsPath)-cne$pinsHash-or(Get-TestHash $fixturePath)-cne$fixtureHash-or(Get-TestHash $dependenciesPath)-cne$dependencyHash){throw 'Test or fixture inputs changed during native execution.'}
            if((Get-TestHash $preservedPath)-cne$preservedHash){throw 'Synthetic preservation sentinel changed.'}
        }catch{if($null-eq$failure){$failure=$_.Exception.Message}}
        $failed=@($script:Cases|Where-Object{$_.status-cne'PASS'}).Count
        if($failed-gt0-and$null-eq$failure){$failure=([string]$failed+' native case(s) failed.')}
        if($script:Cases.Count-ne12-and$null-eq$failure){$failure='Exactly 12 native cases must run.'}
        $receipt=[ordered]@{
            schema='forge.performance.coverage_native_receipt.v1';run_id=$RunId;status=$(if($unsupportedRuntime){'BLOCKED_UNSUPPORTED_NATIVE_RUNTIME'}elseif($null-eq$failure){'PASS'}else{'FAIL'});error=$failure
            started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');fixed_now_utc=$script:Fixtures.now_utc
            powershell_version=$PSVersionTable.PSVersion.ToString();ps_edition=$PSVersionTable.PSEdition;date_kind_string_available=$dateKindAvailable;minimum_powershell_core='7.5'
            run_root=$RunRoot;package_copy_root=$PackageRoot;test_sha256=$testHash;pins_sha256=$pinsHash;fixtures_sha256=$fixtureHash;dependencies_sha256=$dependencyHash
            source_hashes_before=$sourceBefore;source_hashes_after=$sourceAfter;loaded_actual_functions=@($loaded.ToArray());explicit_doubles=$dependencies.doubles
            case_count=$script:Cases.Count;failed_case_count=$failed;cases=@($script:Cases.ToArray());synthetic_fixture_sha256=$preservedHash
            real_data_loaded=$false;app_launched=$false;model_calls=0;network_calls=0;remote_writes=0
            scope='Native actual function ASTs plus disclosed synthetic receipt/state/profile/UI and clock boundary doubles. No full-app, WPF or receipt-authority claim.'
        }
        $writer=[IO.StreamWriter]::new($receiptStream,[Text.UTF8Encoding]::new($false),4096,$true)
        try{$writer.Write(($receipt|ConvertTo-Json -Depth 16));$writer.Flush();$receiptStream.Flush($true)}finally{$writer.Dispose()}
    }
    if($null-ne$failure){throw $failure}
    Write-Output ('Native focused suite passed; supervisor must independently validate '+(Join-Path $RunRoot 'receipt.json'))
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}
