param([Parameter(Mandatory=$true)][string]$DocumentDirectory,
      [Parameter(Mandatory=$true)][string]$QaDirectory)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $DocumentDirectory).Path
New-Item -ItemType Directory -Force -Path $QaDirectory | Out-Null
$destination = (Resolve-Path -LiteralPath $QaDirectory).Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    foreach ($file in Get-ChildItem -LiteralPath $source -Filter '*.docx') {
        $document = $null
        try {
            $document = $word.Documents.Open($file.FullName, $false, $true)
            $document.Repaginate()
            $pdf = Join-Path $destination ($file.BaseName + '.pdf')
            $document.ExportAsFixedFormat($pdf, 17)
            [pscustomobject]@{file=$file.Name; pages=$document.ComputeStatistics(2); pdf=[IO.Path]::GetFileName($pdf)} | ConvertTo-Json -Compress
        } finally {
            if ($null -ne $document) { $document.Close($false) }
        }
    }
} finally {
    $word.Quit()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
