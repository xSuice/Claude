# MA Home Android: baut die APK ohne Gradle (aapt2, javac, d8, apksigner). Aufruf: powershell -File build.ps1
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$sdk = 'C:\Users\andre\Android\sdk'
$bt = Join-Path $sdk 'build-tools\34.0.0'
$jar = Join-Path $sdk 'platforms\android-34\android.jar'
$jdk = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$env:JAVA_HOME = $jdk
$out = Join-Path $here 'out'
$sign = Join-Path $here 'signing'
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force $out, "$out\gen", "$out\classes", "$out\dex", $sign | Out-Null

& "$bt\aapt2.exe" compile --dir "$here\res" -o "$out\res.zip"
& "$bt\aapt2.exe" link -o "$out\base.apk" -I $jar --manifest "$here\AndroidManifest.xml" --java "$out\gen" -R "$out\res.zip" --min-sdk-version 26 --target-sdk-version 34 --version-code 1 --version-name 0.1.0 --auto-add-overlay

$srcs = Get-ChildItem "$here\src", "$out\gen" -Recurse -Filter *.java | ForEach-Object { $_.FullName }
& 'C:\Program Files\Eclipse Adoptium\jdk-17.0.16.8-hotspot\bin\javac.exe' --release 17 -classpath $jar -d "$out\classes" $srcs
$classes = Get-ChildItem "$out\classes" -Recurse -Filter *.class | ForEach-Object { $_.FullName }
& "$bt\d8.bat" --lib $jar --min-api 26 --output "$out\dex" $classes

# classes.dex in die APK legen
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$out\base.apk", 'Update')
[void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, "$out\dex\classes.dex", 'classes.dex')
$zip.Dispose()

& "$bt\zipalign.exe" -f 4 "$out\base.apk" "$out\aligned.apk"

# Eigener Signierschluessel (einmalig, bleibt lokal und wird nicht ins Repo gelegt)
$ks = Join-Path $sign 'ma-home.keystore'
$pw = Join-Path $sign 'ma-home.pass'
if (-not (Test-Path $ks)) {
    $p = -join ((48..57) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    Set-Content -Path $pw -Value $p -NoNewline
    & "$jdk\bin\keytool.exe" -genkeypair -keystore $ks -alias mahome -keyalg RSA -keysize 2048 -validity 10000 -storepass $p -keypass $p -dname 'CN=MA Home, O=Privat, C=DE'
}
$p = Get-Content $pw -Raw
& "$bt\apksigner.bat" sign --ks $ks --ks-pass "pass:$p" --key-pass "pass:$p" --out "$here\MA-Home.apk" "$out\aligned.apk"
& "$bt\apksigner.bat" verify "$here\MA-Home.apk"
Get-Item "$here\MA-Home.apk" | Select-Object Name, Length
