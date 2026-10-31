# Native PowerShell only. Loads actual pinned product function ASTs, not module initializers.
# This is focused headless CSV date guard/importer coverage, not receipt authority or WPF QA.
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
    $fixturePath=Join-Path $PSScriptRoot 'CsvDateFixtures.json';$dependenciesPath=Join-Path $PSScriptRoot 'CsvDateDependencies.json'
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
        Assert-Equal 'forge.csv_date.pins.v1' $pins.schema 'Pinned source schema'
        Assert-Equal $testHash $pins.tests.'Test-ForgeCsvDateAmbiguity.ps1' 'Pinned test hash'
        Assert-Equal $fixtureHash $pins.tests.'CsvDateFixtures.json' 'Pinned fixture hash'
        Assert-Equal $dependencyHash $pins.tests.'CsvDateDependencies.json' 'Pinned dependency hash'
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
        $script:Fixtures=[IO.File]::ReadAllText($fixturePath)|Microsoft.PowerShell.Utility\ConvertFrom-Json -DateKind String
        $script:UiText=@{en=@{};ru=@{};es=@{}};$script:Locale='en';$script:SupportedLocales=@('en','ru','es')
        $script:MessageExact=@{};$script:MessagePatterns=@();$script:UiTextMessageIndex=$null
        $script:InputHashes=[ordered]@{};$script:FixtureIndex=0;$script:StateIndex=0
        $script:StatusText=[pscustomobject]@{Text=''}
        function Get-TestFixtureState {return (Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($script:FixtureStatePath)) -DateKind String)}
        function Set-TestFixtureState($State){[IO.File]::WriteAllText($script:FixtureStatePath,($State|ConvertTo-Json -Depth 60 -Compress),[Text.UTF8Encoding]::new($false))}
        function Reset-TestImport {
            $script:StateIndex++;$script:FixtureStatePath=Join-Path $RunRoot ('state-'+$script:StateIndex+'.json')
            $script:ReadCount=0;$script:WriteCount=0;$script:RefreshCount=0
            $script:Errors=New-Object Collections.Generic.List[string];$script:Questions=New-Object Collections.Generic.List[string];$script:Answers=New-Object Collections.Generic.Queue[bool]
            $script:StatusText.Text=''
            Set-TestFixtureState ([pscustomobject]@{sales_rows=@();sales_imports=@();publication_receipts=@();concepts=@();synthetic_only=$true})
        }
        function New-TestCsv([string[]]$Dates,[string]$Delimiter=',',[string]$Tag=''){
            $script:FixtureIndex++;$path=Join-Path $RunRoot ('input-'+$script:FixtureIndex+'.csv')
            $lines=New-Object Collections.Generic.List[string];$lines.Add((@('Date','ASIN','Units','Royalty (USD)','Title')-join$Delimiter))
            foreach($date in $Dates){$lines.Add((@($date,'SYNTHETIC-A','1','2.50',('SYNTHETIC '+$Tag))-join$Delimiter))}
            $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try{$bytes=[Text.Encoding]::UTF8.GetBytes(($lines-join"`r`n")+"`r`n");$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
            $script:InputHashes[$path]=Get-TestHash $path;return $path
        }
        function Assert-NoImportMutation([string]$Before,[int]$Reads=0,[int]$Prompts=0){
            Assert-Equal $Before (Get-TestHash $script:FixtureStatePath) 'Saved synthetic state bytes unchanged'
            Assert-Equal 0 $script:WriteCount 'No state writes'
            Assert-Equal $Reads $script:ReadCount 'Expected state-read boundary count'
            Assert-Equal $Prompts $script:Questions.Count 'Expected confirmation boundary count'
            Assert-Equal 0 $script:RefreshCount 'No post-write surface refresh'
        }
        # Explicit durable-state and UI seams. CSV capture, date parsing, money,
        # overlap detection, source revalidation, normalization and importer are actual functions.
        function Read-LocalCoreState {$script:ReadCount++;return (Get-TestFixtureState)}
        function Write-LocalCoreState($State){$script:WriteCount++;Set-TestFixtureState $State}
        function Show-Error([string]$Message){$script:Errors.Add($Message)}
        function Confirm([string]$Message,[string]$Title){$script:Questions.Add($Message);if($script:Answers.Count-eq0){throw 'Unexpected confirmation boundary.'};return $script:Answers.Dequeue()}
        function Update-LocalCoreBusinessSurfaces {$script:RefreshCount++}
        function Test-LocalPublicationReceiptAuthority {throw 'Unexpected publication authority call: fixtures have no receipts.'}
        foreach($command in @('Start-LocalGenerationWorker','Invoke-ForgeLocalFlux','Start-Process','Invoke-WebRequest','Invoke-RestMethod','Invoke-Expression','Remove-Item','Copy-Item','Move-Item','Set-Content','Out-File','Add-Type')){
            Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("throw 'Unexpected external or mutation boundary: $command'"))
        }
        foreach($fixture in $script:Fixtures.helper_cases){
            $current=$fixture
            Test-Case $current.name {
                $errorText=$null;$order=$null
                try{$order=Get-CsvSlashDateOrder $current.dates $current.delimiter}catch{$errorText=$_.Exception.Message}
                if($current.error){Assert-True ($null-ne$errorText-and$errorText.Contains($current.error)) 'Exact expected date refusal';Assert-True $errorText.Contains('yyyy-MM-dd') 'Actionable ISO re-export instruction';Assert-True $errorText.Contains('were not changed') 'Preservation statement';Assert-True $errorText.Contains('No import was performed.') 'Explicit no-import statement';Assert-True $errorText.Contains('Example') 'Concrete calendar example'}
                else{Assert-Equal $null $errorText 'Safe dates not rejected';Assert-Equal $current.order $order 'Safe slash order';foreach($expected in $current.expected_dates){$parsed=ConvertFrom-ForgeSalesDate $expected.raw $order;Assert-Equal $expected.iso $parsed.ToString('yyyy-MM-dd') 'Actual parser retains intended calendar date'}}
            }
        }
        foreach($fixture in $script:Fixtures.rejected_imports){
            $current=$fixture
            Test-Case $current.name {
                Reset-TestImport;$path=New-TestCsv $current.dates $current.delimiter;$before=Get-TestHash $script:FixtureStatePath
                Import-LocalSalesCsvFromPath $path
                Assert-Equal 1 $script:Errors.Count 'One visible refusal';Assert-True $script:Errors[0].Contains($current.error) 'Accurate importer error'
                Assert-NoImportMutation $before;Assert-Equal 'Sales CSV import failed.' $script:StatusText.Text 'Importer failed status'
            }
        }
        foreach($fixture in $script:Fixtures.accepted_imports){
            $current=$fixture
            Test-Case $current.name {
                Reset-TestImport;$path=New-TestCsv $current.dates $current.delimiter
                Import-LocalSalesCsvFromPath $path
                Assert-Equal 0 $script:Errors.Count 'No importer error';Assert-Equal 1 $script:ReadCount 'One state read';Assert-Equal 1 $script:WriteCount 'One committed fixture write';Assert-Equal 0 $script:Questions.Count 'No unintended prompt';Assert-Equal 1 $script:RefreshCount 'Refresh after import'
                $state=Get-TestFixtureState;Assert-Equal $current.expected_dates.Count @($state.sales_rows).Count 'All source rows imported';Assert-Equal 1 @($state.sales_imports).Count 'One source import'
                for($i=0;$i-lt$current.expected_dates.Count;$i++){Assert-Equal $current.expected_dates[$i] $state.sales_rows[$i].date 'Correct persisted calendar date';Assert-Equal (Get-TestHash $path) $state.sales_rows[$i].source_file_sha256 'Exact source identity'}
            }
        }
        Test-Case 'locale_does_not_resolve_ambiguity' {
            $saved=[Threading.Thread]::CurrentThread.CurrentCulture
            try{foreach($culture in @('en-US','en-GB','de-DE')){[Threading.Thread]::CurrentThread.CurrentCulture=[Globalization.CultureInfo]::GetCultureInfo($culture);$errorText=$null;try{$null=Get-CsvSlashDateOrder @('03/04/2026') ';'}catch{$errorText=$_.Exception.Message};Assert-True ($null-ne$errorText-and$errorText.Contains('ambiguous slash dates')) 'Locale never establishes slash order'}}finally{[Threading.Thread]::CurrentThread.CurrentCulture=$saved}
        }
        Test-Case 'cancel_overlap_preserves_state_and_input' {
            Reset-TestImport;$first=New-TestCsv @('2026-10-20') ',' 'first';Import-LocalSalesCsvFromPath $first
            Assert-Equal 0 $script:Errors.Count 'Seed import accepted';$path=New-TestCsv @('2026-10-20') ',' 'second'
            $before=Get-TestHash $script:FixtureStatePath;$script:ReadCount=0;$script:WriteCount=0;$script:RefreshCount=0;$script:Answers.Enqueue($false)
            Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Cancel is not an error';Assert-NoImportMutation $before 1 1;Assert-True $script:StatusText.Text.Contains('cancelled') 'Visible cancel status'
        }
        Test-Case 'confirmed_overlap_appends_without_silent_deduplication' {
            Reset-TestImport;$first=New-TestCsv @('2026-10-20') ',' 'first';Import-LocalSalesCsvFromPath $first
            $path=New-TestCsv @('2026-10-20') ',' 'second';$script:Answers.Enqueue($true);Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Confirmed import accepted';Assert-Equal 1 $script:Questions.Count 'One overlap prompt';Assert-Equal 2 $script:WriteCount 'Two distinct committed source imports'
            $state=Get-TestFixtureState;Assert-Equal 2 @($state.sales_rows).Count 'Both genuine source rows kept';Assert-Equal 2 @($state.sales_imports).Count 'Both source identities retained'
        }
        Test-Case 'byte_identical_reimport_is_idempotent' {
            Reset-TestImport;$path=New-TestCsv @('2026-10-20') ',' 'same';Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Initial accepted';$before=Get-TestHash $script:FixtureStatePath;$script:WriteCount=0
            Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Reimport accepted';Assert-Equal 0 $script:WriteCount 'Exact reimport makes no write';Assert-Equal 0 $script:Questions.Count 'Exact reimport has no overlap prompt';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Source reimport byte-preserves state';Assert-True $script:StatusText.Text.Contains('already imported') 'Honest idempotent status'
        }
        Test-Case 'renamed_byte_identical_reimport_keeps_original_source' {
            Reset-TestImport;$first=New-TestCsv @('25/09/2026') ';' 'same';Import-LocalSalesCsvFromPath $first
            $second=New-TestCsv @('25/09/2026') ';' 'same';Assert-Equal (Get-TestHash $first) (Get-TestHash $second) 'Identical bytes under new filename'
            $before=Get-TestHash $script:FixtureStatePath;$script:WriteCount=0;Import-LocalSalesCsvFromPath $second
            Assert-Equal 0 $script:Errors.Count 'Renamed reimport accepted';Assert-Equal 0 $script:WriteCount 'No renamed-source write';Assert-Equal $before (Get-TestHash $script:FixtureStatePath) 'Original source filename and all rows preserved';Assert-Equal 1 @((Get-TestFixtureState).sales_rows).Count 'No duplicate rows'
        }
        Test-Case 'legacy_ambiguous_exact_source_is_refused_unchanged' {
            Reset-TestImport;$path=New-TestCsv @('03/04/2026') ';'
            Set-TestFixtureState ([pscustomobject]@{sales_rows=@([pscustomobject]@{date='2026-04-03';product_id='SYNTHETIC-A';source_file=[IO.Path]::GetFileName($path);source_file_sha256=(Get-TestHash $path);source_row_no=1;owner_note='PRESERVE'});sales_imports=@([pscustomobject]@{file=[IO.Path]::GetFileName($path);sha256=(Get-TestHash $path);rows=1});publication_receipts=@();concepts=@();synthetic_only=$true})
            $before=Get-TestHash $script:FixtureStatePath;Import-LocalSalesCsvFromPath $path
            Assert-Equal 1 $script:Errors.Count 'Previously guessed date does not authorize new interpretation';Assert-True $script:Errors[0].Contains('ambiguous slash dates') 'Actionable refusal';Assert-NoImportMutation $before
        }
        Test-Case 'cancel_exact_source_revalidation_preserves_saved_normalization' {
            Reset-TestImport;$path=New-TestCsv @('2026-10-20') ',' 'same';Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Initial source accepted';$state=Get-TestFixtureState
            $other=Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject ($state.sales_rows[0]|ConvertTo-Json -Depth 60 -Compress) -DateKind String
            $other.source_file_sha256=('f'*64);$other.source_file='other.csv';$state.sales_rows[0].units=9;$state.sales_imports[0].normalization_contract='forge.sales_csv_numeric.v1';$state.sales_rows=@($state.sales_rows)+@($other)
            Set-TestFixtureState $state;$before=Get-TestHash $script:FixtureStatePath;$script:ReadCount=0;$script:WriteCount=0;$script:RefreshCount=0;$script:Answers.Enqueue($false)
            Import-LocalSalesCsvFromPath $path
            Assert-Equal 0 $script:Errors.Count 'Revalidation cancel is not error';Assert-NoImportMutation $before 1 1;Assert-True $script:StatusText.Text.Contains('revalidation cancelled') 'Cancelled saved-source change clearly reported'
        }
        Test-Case 'file_dialog_cancel_does_not_read_or_write' {
            Reset-TestImport;$before=Get-TestHash $script:FixtureStatePath;$script:DialogShown=0
            # Only the outer selector is doubled for this case; real Import-LocalSalesCsv runs.
            function New-Object([string]$TypeName){
                if($TypeName-cne'Microsoft.Win32.OpenFileDialog'){throw 'Unexpected dialog seam type.'}
                $dialog=[pscustomobject]@{Title='';Filter='';FileName='must-not-be-read.csv'}
                $dialog|Add-Member -MemberType ScriptMethod -Name ShowDialog -Value {$script:DialogShown++;return $false};return $dialog
            }
            try{Import-LocalSalesCsv}finally{Microsoft.PowerShell.Management\Remove-Item -LiteralPath Function:New-Object}
            Assert-Equal 1 $script:DialogShown 'Actual selector reached cancel';Assert-Equal 0 $script:Errors.Count 'No cancel error';Assert-NoImportMutation $before
        }
        Test-Case 'actual_message_routing_recognizes_both_date_refusals' {
            foreach($example in @([pscustomobject]@{dates=@('03/04/2026')},[pscustomobject]@{dates=@('25/09/2026','09/25/2026')})){
                $message=$null;try{$null=Get-CsvSlashDateOrder $example.dates ','}catch{$message=$_.Exception.Message}
                Assert-True (-not[string]::IsNullOrWhiteSpace($message)) 'Actual date refusal emitted'
                Assert-True (Test-KnownUiMessage $message) 'Actual existing message router retains actionable date refusal'
                if($example.dates.Count-eq1){Assert-True $message.Contains('03/04/2026 can mean 2026-04-03 (day/month) or 2026-03-04 (month/day)') 'Concrete ambiguous calendar meanings are accurate'}
                Assert-Equal 'Merch Forge could not complete that action. Try again.' (Get-HumanErrorMessage $message) 'Unregistered path would erase the remedy, so known-message route is essential'
            }
        }
        Test-Case 'message_routing_rejects_broad_prefix_or_modified_tail' {
            foreach($message in @('This sales CSV contains ambiguous slash dates. Arbitrary external error.','This sales CSV contains conflicting day/month and month/day slash dates. Arbitrary external error.')){Assert-True (-not(Test-KnownUiMessage $message)) 'No broad error-prefix trust'}
            $message=$null;try{$null=Get-CsvSlashDateOrder @('03/04/2026') ','}catch{$message=$_.Exception.Message}
            Assert-True (-not(Test-KnownUiMessage ($message+' Extra instructions.'))) 'Exact refusal tail required'
            Assert-True (-not(Test-KnownUiMessage ('HTTP 500 '+$message))) 'Server-error safeguards retained'
        }
        Assert-Equal 22 $script:InputHashes.Count 'All expected input CSV fixtures created and tracked'
        $actualNames=@($script:Cases|ForEach-Object{$_.name});Assert-Equal ($pins.expected_case_names-join'|') ($actualNames-join'|') 'Exact ordered native cases'
        $actualFunctions=@($loaded|ForEach-Object{$_.name});Assert-Equal ($pins.expected_function_names-join'|') ($actualFunctions-join'|') 'Exact actual function identity contract'
    } catch {$failure=$_.Exception.Message}
    finally{
        try{
            foreach($source in $pins.sources.PSObject.Properties){$sourceAfter[$source.Name]=Get-TestHash (Join-Path $PackageRoot $source.Name)}
            if($sourceBefore.Count-ne$sourceAfter.Count){throw 'Source count changed during native execution.'};foreach($key in $sourceBefore.Keys){if($sourceBefore[$key]-cne$sourceAfter[$key]){throw ('Source copy changed during native execution: '+$key)}}
            if((Get-TestHash $PSCommandPath)-cne$testHash-or(Get-TestHash $PinsPath)-cne$pinsHash-or(Get-TestHash $fixturePath)-cne$fixtureHash-or(Get-TestHash $dependenciesPath)-cne$dependencyHash){throw 'Test or fixture inputs changed during native execution.'}
            foreach($path in $script:InputHashes.Keys){if((Get-TestHash $path)-cne$script:InputHashes[$path]){throw ('Synthetic source CSV changed: '+$path)}}
            if((Get-TestHash $preservedPath)-cne$preservedHash){throw 'Synthetic preservation sentinel changed.'}
        }catch{if($null-eq$failure){$failure=$_.Exception.Message}}
        $failed=@($script:Cases|Where-Object{$_.status-cne'PASS'}).Count
        if($failed-gt0-and$null-eq$failure){$failure=([string]$failed+' native case(s) failed.')}
        if($script:Cases.Count-ne40-and$null-eq$failure){$failure='Exactly 40 native cases must run.'}
        $receipt=[ordered]@{
            schema='forge.csv_date.native_receipt.v1';run_id=$RunId;status=$(if($unsupportedRuntime){'BLOCKED_UNSUPPORTED_NATIVE_RUNTIME'}elseif($null-eq$failure){'PASS'}else{'FAIL'});error=$failure
            started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');synthetic_only=$true
            powershell_version=$PSVersionTable.PSVersion.ToString();ps_edition=$PSVersionTable.PSEdition;date_kind_string_available=$dateKindAvailable;minimum_powershell_core='7.5'
            run_root=$RunRoot;package_copy_root=$PackageRoot;test_sha256=$testHash;pins_sha256=$pinsHash;fixtures_sha256=$fixtureHash;dependencies_sha256=$dependencyHash
            source_hashes_before=$sourceBefore;source_hashes_after=$sourceAfter;loaded_actual_functions=@($loaded.ToArray());explicit_doubles=$dependencies.doubles
            input_csv_hashes=$script:InputHashes;case_count=$script:Cases.Count;failed_case_count=$failed;cases=@($script:Cases.ToArray());synthetic_fixture_sha256=$preservedHash
            real_data_loaded=$false;app_launched=$false;model_calls=0;network_calls=0;remote_writes=0
            scope='Actual CSV capture/date/import/reimport functions plus disclosed synthetic durable-state/UI/confirmation seams. No full-app, WPF, actual state-store or publication-authority claim.'
        }
        $writer=[IO.StreamWriter]::new($receiptStream,[Text.UTF8Encoding]::new($false),4096,$true)
        try{$writer.Write(($receipt|ConvertTo-Json -Depth 16));$writer.Flush();$receiptStream.Flush($true)}finally{$writer.Dispose()}
    }
    if($null-ne$failure){throw $failure}
    Write-Output ('Native focused suite passed; supervisor must independently validate '+(Join-Path $RunRoot 'receipt.json'))
}finally{if($null-ne$receiptStream){$receiptStream.Dispose()};if($null-ne$claim){$claim.Dispose()}}
