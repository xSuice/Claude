# Einmalig von Philipp auszufuehren: nimmt die Android-SDK-Lizenzen an (Eingabe y) und installiert die benoetigten Teile.
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'
$sdk = 'C:\Users\andre\Android\sdk'
& "$sdk\cmdline-tools\latest\bin\sdkmanager.bat" --sdk_root=$sdk --licenses
& "$sdk\cmdline-tools\latest\bin\sdkmanager.bat" --sdk_root=$sdk "platform-tools" "platforms;android-34" "build-tools;34.0.0"
Write-Host "Fertig. Jetzt Claude sagen: SDK ist installiert."
