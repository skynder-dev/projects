# Native PowerShell only. Loads actual pinned product function ASTs, not module initializers.
# This is focused headless aggregation/rendering coverage, not receipt authority or WPF QA.
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
    $fixturePath=Join-Path $PSScriptRoot 'PerformanceFixtures.json';$dependenciesPath=Join-Path $PSScriptRoot 'dependencies.json'
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
        Assert-Equal 'forge.performance.pins.v1' $pins.schema 'Pinned source schema'
        Assert-Equal $testHash $pins.tests.'Test-ForgePerformanceMetrics.ps1' 'Pinned test hash'
        Assert-Equal $fixtureHash $pins.tests.'PerformanceFixtures.json' 'Pinned fixture hash'
        Assert-Equal $dependencyHash $pins.tests.'dependencies.json' 'Pinned dependency hash'
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
        Test-Case 'mixed_currency_not_summed' {
            $state=New-TestState (Get-FixtureRows 'mixed');$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow;$p=Get-TestProduct $ins
            Assert-Number 3.75 $p.metrics.sales30 'Fractional product units'
            Assert-Equal 2 @($p.metrics.royalty_currencies).Count 'Two currencies retained'
            Assert-Number 10 (Get-TestCurrency $p.metrics 'USD').royalties30 'USD retained'
            Assert-Number 20 (Get-TestCurrency $p.metrics 'EUR').royalties30 'EUR retained'
            Assert-True ($p.metrics.royalties30-ne30) 'No mixed-currency scalar 30'
            Assert-True ($p.roy30-ne30) 'No mixed-currency legacy scalar 30'
            $label=Format-LocalRoyaltyTotal $p.metrics 30
            Assert-True ($label.Contains('USD 10.00')-and$label.Contains('EUR 20.00')) 'Both true currency labels'
            Assert-True (-not$label.Contains('$')) 'No fabricated dollar symbol'
            Assert-Agreement $home $ins.products
        }
        Test-Case 'ranking_uses_units_not_raw_money' {
            $state=New-TestState (Get-FixtureRows 'ranking');$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 2 @($ins.leaders).Count 'Both complete products ranked'
            Assert-Equal 'B' $ins.leaders[0].product_id 'USD 20 with two units beats JPY 1000 with one unit'
        }
        Test-Case 'ranking_ties_are_stable_not_money' {
            $rows=@((New-TestRow -Id B -Units 1 -Royalty 1000 -Currency JPY),(New-TestRow -Id A -Units 1 -Royalty 20 -Currency USD))
            $ins=Get-ForgePerformanceInsights (New-TestState $rows) $script:FixedNow
            Assert-Equal 'A' $ins.leaders[0].product_id 'Stable product key breaks equal-unit tie'
        }
        Test-Case 'unverified_999_and_99_excluded_unknown' {
            $state=New-TestState (Get-FixtureRows 'unknown_numeric');$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow;$p=Get-TestProduct $ins
            Assert-Number 2 $p.metrics.sales30 'Unverified 99 excluded';Assert-Number 10 (Get-TestCurrency $p.metrics 'USD').royalties30 'Unverified 999 excluded'
            Assert-Equal 1 ([int]$p.metrics.units_unknown30) 'Unknown units reported';Assert-Equal 1 ([int]$p.metrics.royalty_unknown30) 'Unknown royalty reported'
            Assert-True (@($ins.leaders|Where-Object{$_.product_id-ceq'A'}).Count-eq0) 'Incomplete unit total must not rank'
            Assert-Equal (Get-UiText 'money.unverified' 'Unverified') (Format-LocalSalesUnits $p.metrics 30) 'Unknown unit label'
            Assert-True (-not(Format-LocalRoyaltyTotal $p.metrics 30).Contains('999')) 'Unknown royalty not displayed as known'
            Assert-Agreement $home $ins.products
        }
        Test-Case 'unverified_receipt_excluded_and_unknown_product' {
            $state=New-TestState @((New-TestRow -Id UNKNOWN -Units 99 -Royalty 999))
            $state.publication_receipts+= [pscustomobject]@{concept_key='concept-C';channel='amazon_merch';marketplace='synthetic';product_id='UNKNOWN';published_at='2026-01-01T00:00:00Z';fixture_verified=$false}
            $home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Number 0 $home.sales30 'Unverified receipt excluded';Assert-Equal 1 ([int]$home.unlinked_rows) 'Unlinked count'
            Assert-True (@($ins.attention|Where-Object{$_.kind-ceq'unknown'-and$_.args[0]-ceq'UNKNOWN'}).Count-eq1) 'Unknown product explicitly reported'
            Assert-True (@($ins.products|Where-Object{$_.product_id-ceq'UNKNOWN'}).Count-eq0) 'No product from unverified receipt'
        }
        Test-Case 'utc_day_29_in_30_out_89_in_90_out' {
            $state=New-TestState (Get-FixtureRows 'boundaries');$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow;$m=(Get-TestProduct $ins).metrics
            Assert-Number 1 $m.sales30 'Only day 29 in 30-day window';Assert-Number 7 $m.sales90 'Day 89 in and day 90 out'
            Assert-Number 10 (Get-TestCurrency $m 'USD').royalties30 '30-day royalty boundary';Assert-Number 70 (Get-TestCurrency $m 'USD').royalties90 '90-day royalty boundary'
            Assert-Equal 1 ([int]$m.observed_rows30) '30-day observed rows';Assert-Equal 3 ([int]$m.observed_rows90) '90-day observed rows'
            Assert-Equal '2026-09-25' $m.window_start30 'Fixed 30-day start';Assert-Equal '2026-07-27' $m.window_start90 'Fixed 90-day start';Assert-Equal '2026-10-24' $m.window_end 'Fixed UTC date'
            Assert-Agreement $home $ins.products
        }
        Test-Case 'utc_day_6_in_7_out' {
            $m=Get-LocalSalesMetrics (New-TestState (Get-FixtureRows 'seven_day_boundaries')) $script:FixedNow
            Assert-Number 1 $m.sales7 '7-day boundary';Assert-Number 10 (Get-TestCurrency $m 'USD').royalties7 '7-day royalty boundary'
        }
        Test-Case 'future_and_undated_rows_excluded' {
            $future=New-TestRow -Age -1 -Units 99 -Royalty 999;$undated=New-TestRow -Units 99 -Royalty 999;$undated.date='not-a-date'
            $state=New-TestState @($future,$undated);$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Number 0 $home.sales90 'No future or undated units';Assert-Number 0 $home.royalties90 'No future or undated royalties';Assert-Equal 1 ([int]$home.future_rows) 'Future row reported';Assert-Equal 1 ([int]$home.undated_rows) 'Undated row reported';Assert-Agreement $home $ins.products
        }
        Test-Case 'refund_and_zero_are_observed_transactions' {
            $state=New-TestState (Get-FixtureRows 'refund_zero');$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            $a=(Get-TestProduct $ins 'A').metrics;$b=(Get-TestProduct $ins 'B').metrics
            Assert-Number -1.25 $a.sales30 'Refund units retained';Assert-Number -10 (Get-TestCurrency $a 'USD').royalties30 'Refund amount retained';Assert-Number 0 $b.sales30 'Netzero units retained'
            Assert-Equal 1 ([int]$a.observed_rows30) 'Refund is observed';Assert-Equal 1 ([int]$b.observed_rows30) 'Zero is observed';Assert-Equal 2 ([int]$home.observed_rows30) 'Both observed in Home';Assert-Agreement $home $ins.products
        }
        Test-Case 'aggregate_and_each_product_agree_all_windows' {
            $state=New-TestState (Get-FixtureRows 'agreement');$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Agreement $home $ins.products;Assert-Number 3.75 $home.sales30 'Known aggregate 30-day units';Assert-Number 4 $home.sales90 'Known aggregate 90-day units';Assert-Equal 1 ([int]$home.unlinked_rows) 'Unknown product excluded'
        }
        foreach($field in @('units','royalty')){
            foreach($variant in @('missing','null','blank','NaN','positive_infinity','negative_infinity','too_large','unreadable','array','object','boolean','missing_flag','false_flag','string_true_flag')){
                $currentField=$field;$currentVariant=$variant
                Test-Case ($field+'_'+$variant+'_is_unknown') {
                    $row=New-TestRow
                    switch($currentVariant){
                        'missing'{$row.PSObject.Properties.Remove($currentField)}
                        'null'{$row.$currentField=$null}
                        'blank'{$row.$currentField=' '}
                        'NaN'{$row.$currentField=[double]::NaN}
                        'positive_infinity'{$row.$currentField=[double]::PositiveInfinity}
                        'negative_infinity'{$row.$currentField=[double]::NegativeInfinity}
                        'too_large'{$row.$currentField=1000000000001.0}
                        'unreadable'{$row.$currentField='not-an-amount'}
                        'array'{$row.$currentField=@(1)}
                        'object'{$row.$currentField=[pscustomobject]@{value=10}}
                        'boolean'{$row.$currentField=$true}
                        'missing_flag'{$row.PSObject.Properties.Remove($currentField+'_amount_verified')}
                        'false_flag'{$row.($currentField+'_amount_verified')=$false}
                        'string_true_flag'{$row.($currentField+'_amount_verified')='true'}
                    }
                    $state=New-TestState @($row);$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow;$product=Get-TestProduct $ins
                    Assert-MetricsUnknown $home $currentField;Assert-MetricsUnknown $product.metrics $currentField;Assert-Agreement $home $ins.products
                    if($currentVariant-ceq'array'){
                        $flagArrayRow=New-TestRow;$flagArrayRow.($currentField+'_amount_verified')=@($true)
                        $flagArrayState=New-TestState @($flagArrayRow)
                        $flagArrayHome=Get-LocalSalesMetrics $flagArrayState $script:FixedNow
                        $flagArrayInsights=Get-ForgePerformanceInsights $flagArrayState $script:FixedNow
                        Assert-MetricsUnknown $flagArrayHome $currentField
                        Assert-MetricsUnknown (Get-TestProduct $flagArrayInsights).metrics $currentField
                    }
                }
            }
        }
        Test-Case 'singleton_currency_array_is_unknown' {
            $row=New-TestRow;$row.currency=@('USD');$state=New-TestState @($row)
            $home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-MetricsUnknown $home 'royalty';Assert-MetricsUnknown (Get-TestProduct $ins).metrics 'royalty'
            Assert-Number 1.25 $home.sales30 'Valid units independent of invalid currency shape';Assert-Agreement $home $ins.products
        }
        Test-Case 'singleton_date_array_is_undated' {
            $row=New-TestRow;$row.date=@('2026-10-23');$state=New-TestState @($row)
            $home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Equal 1 ([int]$home.undated_rows) 'Array date is not silently scalarized'
            Assert-Equal 0 ([int]$home.observed_rows90) 'Undated array row not observed';Assert-Number 0 $home.sales90 'Array date units excluded'
            Assert-Number 0 $home.royalties90 'Array date royalties excluded';Assert-Agreement $home $ins.products
        }
        Test-Case 'legacy_v1_with_true_numeric_flags_remains_valid' {
            $row=New-TestRow -Units 1.25 -Royalty 10
            Add-OrSetProperty $row 'normalization_contract' 'forge.sales_csv_numeric.v1'
            Add-OrSetProperty $row 'source_file_sha256' ('a'*64);Add-OrSetProperty $row 'source_row_no' 1
            Add-OrSetProperty $row 'source_file' 'SYNTHETIC-LEGACY.csv'
            $state=New-TestState @($row);$home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-Number 1.25 $home.sales30 'Legacy verified units stay valid';Assert-Number 10 (Get-TestCurrency $home 'USD').royalties30 'Legacy verified royalty stays valid'
            Assert-Equal 0 ([int]$home.units_unknown30) 'No legacy-only unit downgrade';Assert-Equal 0 ([int]$home.royalty_unknown30) 'No legacy-only money downgrade'
            Assert-Equal 'forge.sales_csv_numeric.v1' $row.normalization_contract 'Legacy contract preserved';Assert-Equal ('a'*64) $row.source_file_sha256 'Source hash preserved';Assert-Equal 1 $row.source_row_no 'Source ordinal preserved'
            Assert-Agreement $home $ins.products
        }
        Test-Case 'legacy_source_identity_without_numeric_flags_stays_unknown_unchanged' {
            $row=New-TestRow -Units 99 -Royalty 999
            $row.PSObject.Properties.Remove('units_amount_verified');$row.PSObject.Properties.Remove('royalty_amount_verified')
            Add-OrSetProperty $row 'normalization_contract' 'forge.sales_csv_numeric.v1'
            Add-OrSetProperty $row 'source_file_sha256' ('a'*64);Add-OrSetProperty $row 'source_row_no' 1
            Add-OrSetProperty $row 'source_file' 'SYNTHETIC-LEGACY.csv'
            $state=New-TestState @($row)
            # Receipt acceptance is the explicitly disclosed synthetic authority seam.
            # Source identity/package linkage must not stand in for numeric evidence.
            Reconcile-LocalSalesLinks $state
            Assert-True $row.linked 'Product is linked before preservation snapshot'
            $before=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($row|ConvertTo-Json -Depth 12 -Compress)))
            $home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
            Assert-MetricsUnknown $home 'units';Assert-MetricsUnknown $home 'royalty'
            Assert-MetricsUnknown (Get-TestProduct $ins).metrics 'units';Assert-MetricsUnknown (Get-TestProduct $ins).metrics 'royalty'
            Assert-Equal $before ([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($row|ConvertTo-Json -Depth 12 -Compress)))) 'Legacy row serialized bytes preserved'
            Assert-True ($null-eq$row.PSObject.Properties['units_amount_verified']-and$null-eq$row.PSObject.Properties['royalty_amount_verified']) 'Missing evidence not invented'
            Assert-Agreement $home $ins.products
        }
        Test-Case 'es_ES_culture_does_not_change_numeric_totals' {
            $oldCulture=[Threading.Thread]::CurrentThread.CurrentCulture;$oldUiCulture=[Threading.Thread]::CurrentThread.CurrentUICulture
            try{
                [Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo('es-ES')
                [Threading.Thread]::CurrentThread.CurrentUICulture=[Globalization.CultureInfo]::GetCultureInfo('es-ES')
                $state=New-TestState @((New-TestRow -Units 1.25 -Royalty 10.5),(New-TestRow -Units '2.5' -Royalty '20.25'))
                $home=Get-LocalSalesMetrics $state $script:FixedNow;$ins=Get-ForgePerformanceInsights $state $script:FixedNow
                Assert-Number 3.75 $home.sales30 'Invariant native numeric and string unit parsing'
                Assert-Number 30.75 (Get-TestCurrency $home 'USD').royalties30 'Invariant native numeric and string royalty parsing'
                Assert-Equal '3.75' (Format-LocalSalesUnits $home 30) 'Invariant fractional formatting'
                Assert-Equal 'USD 30.75' (Format-LocalRoyaltyTotal $home 30) 'Invariant currency formatting';Assert-Agreement $home $ins.products
            }finally{[Threading.Thread]::CurrentThread.CurrentCulture=$oldCulture;[Threading.Thread]::CurrentThread.CurrentUICulture=$oldUiCulture}
        }
        # Clock-only adapter: delegates to the original production ScriptBlock.
        # No alternate business logic; only default time is fixed for the real renderer.
        $script:ActualInsights=(Get-Command Get-ForgePerformanceInsights -CommandType Function).ScriptBlock
        function Get-ForgePerformanceInsights($State,[datetime]$NowUtc=$script:FixedNow){& $script:ActualInsights $State $NowUtc}
        foreach($name in @('HomeMetricAttentionValue','HomeMetricPublishedValue','HomeMetricPublishedHint','HomeMetricSalesValue','HomeMetricSalesHint','HomeMetricRoyaltiesValue','HomeMetricRoyaltiesHint','HomeMetricAttentionHint')){Set-Variable -Name $name -Value $null}
        $expectedLabels=@{
            en=@{units='Unverified';money='1 row(s): currency or amount unverified'}
            ru=@{units='Не проверено';money='Строк с непроверенной валютой или суммой: 1'}
            es=@{units='Sin verificar';money='1 fila(s): moneda o importe sin verificar'}
        }
        foreach($locale in @('en','ru','es')){
            $currentLocale=$locale
            Test-Case ('render_'+$locale+'_currency_and_fractional_labels') {
                $script:Locale=$currentLocale;$script:CurrentFixtureState=New-TestState (Get-FixtureRows 'mixed')
                $PerformanceLeadersText=[pscustomobject]@{Text=''};$PerformanceAttentionText=[pscustomobject]@{Text=''}
                Update-PerformanceInsightsSurface
                $text=$PerformanceLeadersText.Text
                Assert-True ($text.Contains('USD 10.00')-and$text.Contains('EUR 20.00')) 'Renderer preserves both currency codes'
                Assert-True $text.Contains('3.75') 'Renderer preserves fractional units'
                Assert-True (-not$text.Contains('$')) 'Renderer does not fabricate dollars'
                Assert-True (-not$script:UiText[$currentLocale]['perf.leader.line'].Contains('$')) 'Locale template has no dollar symbol'
                $unknown=Get-LocalSalesMetrics (New-TestState @((New-TestRow -Verified $false -Units 99 -Royalty 999))) $script:FixedNow
                $unitText=Format-LocalSalesUnits $unknown 30;$moneyText=Format-LocalRoyaltyTotal $unknown 30
                Assert-True (-not[string]::IsNullOrWhiteSpace($unitText)) 'Unknown units have label';Assert-True (-not[string]::IsNullOrWhiteSpace($moneyText)) 'Unknown money has label'
                Assert-Equal $expectedLabels[$currentLocale].units $unitText 'Concrete locale unknown unit label'
                Assert-Equal $expectedLabels[$currentLocale].money $moneyText 'Concrete locale unknown royalty label'
                Assert-Equal $expectedLabels[$currentLocale].units (Format-LocalRoyaltyTotal $unknown 30 -Compact) 'Concrete locale compact unknown label'
                Assert-True (-not$unitText.Contains('99') -and -not $moneyText.Contains('999') -and -not $moneyText.Contains('$')) 'Unknown values not fabricated'
            }
        }
        $script:Locale='en'
        Set-Item -Path Function:Get-ForgePerformanceInsights -Value $script:ActualInsights
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
        if($script:Cases.Count-ne46-and$null-eq$failure){$failure='Exactly 46 native cases must run.'}
        $receipt=[ordered]@{
            schema='forge.performance.native_receipt.v1';run_id=$RunId;status=$(if($unsupportedRuntime){'BLOCKED_UNSUPPORTED_NATIVE_RUNTIME'}elseif($null-eq$failure){'PASS'}else{'FAIL'});error=$failure
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
