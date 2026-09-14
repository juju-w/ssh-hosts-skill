$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
public struct SshHostsCredential {
    public UInt32 Flags;
    public UInt32 Type;
    public string TargetName;
    public string Comment;
    public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
    public UInt32 CredentialBlobSize;
    public IntPtr CredentialBlob;
    public UInt32 Persist;
    public UInt32 AttributeCount;
    public IntPtr Attributes;
    public string TargetAlias;
    public string UserName;
}

public static class SshHostsCredentialNative {
    [DllImport("Advapi32.dll", EntryPoint = "CredWriteW", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CredWrite([In] ref SshHostsCredential credential, UInt32 flags);

    [DllImport("Advapi32.dll", EntryPoint = "CredReadW", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CredRead(string target, UInt32 type, UInt32 flags, out IntPtr credential);

    [DllImport("Advapi32.dll", EntryPoint = "CredDeleteW", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CredDelete(string target, UInt32 type, UInt32 flags);

    [DllImport("Advapi32.dll", EntryPoint = "CredFree")]
    public static extern void CredFree(IntPtr buffer);
}
"@

function Throw-LastCredentialError {
    $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $message = [ComponentModel.Win32Exception]::new($code).Message
    throw "Credential Manager failed with Win32 error $code`: $message"
}

$target = "dev.ssh-hosts.smoke/" + [Guid]::NewGuid().ToString("N")
$password = [Guid]::NewGuid().ToString("N")
$bytes = [Text.Encoding]::UTF8.GetBytes($password)
$blob = [Runtime.InteropServices.Marshal]::AllocHGlobal($bytes.Length)
[Runtime.InteropServices.Marshal]::Copy($bytes, 0, $blob, $bytes.Length)
$readPointer = [IntPtr]::Zero
$created = $false

try {
    $credential = New-Object SshHostsCredential
    $credential.Type = 1
    $credential.TargetName = $target
    $credential.CredentialBlobSize = $bytes.Length
    $credential.CredentialBlob = $blob
    $credential.Persist = 2
    $credential.UserName = "ssh-hosts-smoke"

    if (-not [SshHostsCredentialNative]::CredWrite([ref]$credential, 0)) {
        Throw-LastCredentialError
    }
    $created = $true

    if (-not [SshHostsCredentialNative]::CredRead($target, 1, 0, [ref]$readPointer)) {
        Throw-LastCredentialError
    }
    $readCredential = [Runtime.InteropServices.Marshal]::PtrToStructure(
        $readPointer,
        [type][SshHostsCredential]
    )
    $readBytes = New-Object byte[] $readCredential.CredentialBlobSize
    [Runtime.InteropServices.Marshal]::Copy(
        $readCredential.CredentialBlob,
        $readBytes,
        0,
        $readBytes.Length
    )
    if ([Text.Encoding]::UTF8.GetString($readBytes) -ne $password) {
        throw "Credential Manager returned different synthetic data"
    }

    if (-not [SshHostsCredentialNative]::CredDelete($target, 1, 0)) {
        Throw-LastCredentialError
    }
    $created = $false
    Write-Output "credential_manager_roundtrip=ok"
    Write-Output "synthetic_credential_removed=true"
}
finally {
    if ($readPointer -ne [IntPtr]::Zero) {
        [SshHostsCredentialNative]::CredFree($readPointer)
    }
    if ($created) {
        [void][SshHostsCredentialNative]::CredDelete($target, 1, 0)
    }
    [Runtime.InteropServices.Marshal]::FreeHGlobal($blob)
}
