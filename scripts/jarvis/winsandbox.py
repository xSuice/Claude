"""Windows sandbox for JARVIS PC steps (no admin rights, no WSL/Docker needed).

Isolation = AppContainer + Job Object:
- AppContainer "MA.JARVIS.PCWorker": no network unless network=True (capability internetClient); file access only where
  the container SID is granted (the per-step work folder) plus what Windows grants to ALL APPLICATION PACKAGES
  (Windows, Program Files incl. the JDK, read-only). No access to the user profile, Documents, ~/.ssh, ~/.claude, HKCU.
- Job Object: memory cap for the whole tree, max. process count, hard CPU cap, below-normal priority, UI limits
  (no clipboard, no desktop switch, no logoff), kill-on-close; wall-clock timeout kills the whole tree.
- Only stdout/stderr (one log file opened by us) are inherited; environment is rebuilt from scratch.

    from winsandbox import Sandbox, Limits
    r = Sandbox().run(['javac', 'X.java'], workdir, Limits(mem_mb=1536, procs=16, cpu_pct=50, timeout_s=900))
    r.code, r.output, r.timed_out, r.peak_mem_mb
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import tempfile
import time
from ctypes import wintypes as wt
from dataclasses import dataclass, field
from pathlib import Path

CONTAINER = 'MA.JARVIS.PCWorker'
INTERNET_CLIENT_SID = 'S-1-15-3-1'
# Win32-App-Isolation capability with list/traverse/read-attributes on volume roots (C:\ has an ACE for it).
# Without it every Java File.createTempFile fails (GetVolumeInformation on C:\ -> access denied), i.e. jar and Gradle.
VOLUME_ROOT_CAP = 'isolatedWin32-volumeRootMinimal'
ROOT = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ma-jarvis' / 'pcwork'

if os.name == 'nt':
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    adv = ctypes.WinDLL('advapi32', use_last_error=True)
    uenv = ctypes.WinDLL('userenv', use_last_error=True)
    kbase = ctypes.WinDLL('kernelbase', use_last_error=True)
    _P, _H, _D = ctypes.c_void_p, wt.HANDLE, wt.DWORD
    for _f, _a, _r in (
            (k32.CreateFileW, [wt.LPCWSTR, _D, _D, _P, _D, _D, _H], _H),
            (k32.CreateJobObjectW, [_P, wt.LPCWSTR], _H),
            (k32.SetInformationJobObject, [_H, ctypes.c_int, _P, _D], wt.BOOL),
            (k32.QueryInformationJobObject, [_H, ctypes.c_int, _P, _D, _P], wt.BOOL),
            (k32.AssignProcessToJobObject, [_H, _H], wt.BOOL),
            (k32.TerminateJobObject, [_H, wt.UINT], wt.BOOL),
            (k32.TerminateProcess, [_H, wt.UINT], wt.BOOL),
            (k32.WaitForSingleObject, [_H, _D], _D),
            (k32.GetExitCodeProcess, [_H, ctypes.POINTER(_D)], wt.BOOL),
            (k32.ResumeThread, [_H], _D),
            (k32.CloseHandle, [_H], wt.BOOL),
            (k32.LocalFree, [_P], _P),
            (k32.InitializeProcThreadAttributeList, [_P, _D, _D, ctypes.POINTER(ctypes.c_size_t)], wt.BOOL),
            (k32.UpdateProcThreadAttribute, [_P, _D, ctypes.c_size_t, _P, ctypes.c_size_t, _P, _P], wt.BOOL),
            (k32.DeleteProcThreadAttributeList, [_P], None),
            (k32.CreateProcessW, [wt.LPCWSTR, wt.LPWSTR, _P, _P, wt.BOOL, _D, _P, wt.LPCWSTR, _P, _P], wt.BOOL),
            (adv.ConvertStringSidToSidW, [wt.LPCWSTR, ctypes.POINTER(_P)], wt.BOOL),
            (adv.ConvertSidToStringSidW, [_P, ctypes.POINTER(wt.LPWSTR)], wt.BOOL),
            (uenv.CreateAppContainerProfile, [wt.LPCWSTR, wt.LPCWSTR, wt.LPCWSTR, _P, _D, ctypes.POINTER(_P)], ctypes.c_long),
            (uenv.DeriveAppContainerSidFromAppContainerName, [wt.LPCWSTR, ctypes.POINTER(_P)], ctypes.c_long),
            (kbase.DeriveCapabilitySidsFromName, [wt.LPCWSTR, ctypes.POINTER(_P), ctypes.POINTER(_D), ctypes.POINTER(_P),
                                                  ctypes.POINTER(_D)], wt.BOOL)):
        _f.argtypes, _f.restype = _a, _r


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Sid', ctypes.c_void_p), ('Attributes', wt.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [('AppContainerSid', ctypes.c_void_p), ('Capabilities', ctypes.POINTER(SID_AND_ATTRIBUTES)),
                ('CapabilityCount', wt.DWORD), ('Reserved', wt.DWORD)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [('cb', wt.DWORD), ('lpReserved', wt.LPWSTR), ('lpDesktop', wt.LPWSTR), ('lpTitle', wt.LPWSTR),
                ('dwX', wt.DWORD), ('dwY', wt.DWORD), ('dwXSize', wt.DWORD), ('dwYSize', wt.DWORD),
                ('dwXCountChars', wt.DWORD), ('dwYCountChars', wt.DWORD), ('dwFillAttribute', wt.DWORD),
                ('dwFlags', wt.DWORD), ('wShowWindow', wt.WORD), ('cbReserved2', wt.WORD), ('lpReserved2', ctypes.c_void_p),
                ('hStdInput', wt.HANDLE), ('hStdOutput', wt.HANDLE), ('hStdError', wt.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [('StartupInfo', STARTUPINFOW), ('lpAttributeList', ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wt.HANDLE), ('hThread', wt.HANDLE), ('dwProcessId', wt.DWORD), ('dwThreadId', wt.DWORD)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
                                                   'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
                ('LimitFlags', wt.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t), ('MaximumWorkingSetSize', ctypes.c_size_t),
                ('ActiveProcessLimit', wt.DWORD), ('Affinity', ctypes.c_size_t), ('PriorityClass', wt.DWORD),
                ('SchedulingClass', wt.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION), ('IoInfo', IO_COUNTERS),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(ctypes.Structure):
    _fields_ = [('ControlFlags', wt.DWORD), ('CpuRate', wt.DWORD)]


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [('TotalUserTime', ctypes.c_longlong), ('TotalKernelTime', ctypes.c_longlong),
                ('ThisPeriodTotalUserTime', ctypes.c_longlong), ('ThisPeriodTotalKernelTime', ctypes.c_longlong),
                ('TotalPageFaultCount', wt.DWORD), ('TotalProcesses', wt.DWORD), ('ActiveProcesses', wt.DWORD),
                ('TotalTerminatedProcesses', wt.DWORD)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('nLength', wt.DWORD), ('lpSecurityDescriptor', ctypes.c_void_p), ('bInheritHandle', wt.BOOL)]


# constants
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_SUSPENDED = 0x4
CREATE_UNICODE_ENVIRONMENT = 0x400
CREATE_NO_WINDOW = 0x08000000
BELOW_NORMAL_PRIORITY_CLASS = 0x4000
STARTF_USESTDHANDLES = 0x100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
SE_GROUP_ENABLED = 0x4
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x8
JOB_OBJECT_LIMIT_PRIORITY_CLASS = 0x20
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectBasicAccountingInformation = 1
JobObjectBasicUIRestrictions = 4
JobObjectExtendedLimitInformation = 9
JobObjectCpuRateControlInformation = 15
JOB_OBJECT_CPU_RATE_CONTROL_ENABLE = 0x1
JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP = 0x4
JOB_OBJECT_UILIMIT_ALL = 0xFF  # handles, clipboard r/w, system parameters, display settings, global atoms, desktop, logoff
WAIT_TIMEOUT = 0x102
GENERIC_READ, GENERIC_WRITE = 0x80000000, 0x40000000
FILE_SHARE_RW = 0x3
OPEN_EXISTING, CREATE_ALWAYS = 3, 2
INVALID = ctypes.c_void_p(-1).value
E_ALREADY_EXISTS = -2147024713  # HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS)


@dataclass
class Limits:
    mem_mb: int = 1536          # whole process tree
    procs: int = 16             # simultaneously active processes
    cpu_pct: int = 50           # hard cap, % of all logical CPUs
    timeout_s: int = 900
    network: bool = False       # True = capability internetClient (outbound internet; still no file access outside)


@dataclass
class Result:
    code: int
    output: str
    timed_out: bool
    seconds: float
    peak_mem_mb: float
    processes: int
    info: dict = field(default_factory=dict)


def _check(ok, what):
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), what)


def container_sid() -> str:
    """Create (once) or open the AppContainer profile; returns the container SID string."""
    sid = ctypes.c_void_p()
    hr = uenv.CreateAppContainerProfile(CONTAINER, 'MA JARVIS PC-Worker', 'Isolierte Ausführung von JARVIS-PC-Schritten',
                                        None, 0, ctypes.byref(sid))
    if hr == E_ALREADY_EXISTS:
        hr = uenv.DeriveAppContainerSidFromAppContainerName(CONTAINER, ctypes.byref(sid))
    if hr != 0:
        raise OSError(f'AppContainer-Profil nicht verfügbar (HRESULT {hr & 0xFFFFFFFF:#x})')
    s = wt.LPWSTR()
    _check(adv.ConvertSidToStringSidW(sid, ctypes.byref(s)), 'ConvertSidToStringSid')
    try:
        return s.value
    finally:
        k32.LocalFree(s)


def capability_sid(name: str) -> str:
    """SID string of a named capability (S-1-15-3-...), derived like Windows does for package manifests."""
    groups, ng, caps, nc = ctypes.c_void_p(), wt.DWORD(), ctypes.c_void_p(), wt.DWORD()
    _check(kbase.DeriveCapabilitySidsFromName(name, ctypes.byref(groups), ctypes.byref(ng), ctypes.byref(caps),
                                              ctypes.byref(nc)), f'DeriveCapabilitySidsFromName {name}')
    arr = ctypes.cast(caps, ctypes.POINTER(ctypes.c_void_p))
    s = wt.LPWSTR()
    _check(nc.value >= 1 and adv.ConvertSidToStringSidW(arr[0], ctypes.byref(s)), 'ConvertSidToStringSid cap')
    try:
        return s.value
    finally:
        k32.LocalFree(s)


def _sid_from_string(text: str) -> ctypes.c_void_p:
    p = ctypes.c_void_p()
    _check(adv.ConvertStringSidToSidW(text, ctypes.byref(p)), 'ConvertStringSidToSid')
    return p


def grant(path: Path, sid: str, rights: str = 'F') -> None:
    """Grant the container SID access to path (inherited by everything created below it)."""
    r = subprocess.run(['icacls', str(path), '/grant', f'*{sid}:(OI)(CI){rights}', '/T', '/C', '/Q'],
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        raise OSError(f'icacls fehlgeschlagen: {r.stdout}{r.stderr}')


def new_workdir(prefix: str = 'step') -> Path:
    """Fresh folder below ROOT that the container may use (work/ is granted, the log next to it is not)."""
    ROOT.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix=f'{prefix}-', dir=ROOT))
    (d / 'work').mkdir()
    grant(d / 'work', container_sid())
    return d / 'work'


def _env_block(env: dict) -> ctypes.Array:
    text = ''.join(f'{k}={v}\0' for k, v in sorted(env.items(), key=lambda kv: kv[0].upper())) + '\0'
    return ctypes.create_unicode_buffer(text, len(text))


def _cmdline(argv: list[str]) -> str:
    return subprocess.list2cmdline(argv)


def base_env(work: Path, extra: dict | None = None) -> dict:
    sysroot = os.environ.get('SystemRoot', r'C:\Windows')
    tmp, home = work / '.tmp', work / '.home'
    tmp.mkdir(exist_ok=True)
    home.mkdir(exist_ok=True)
    path = [p for p in os.environ.get('PATH', '').split(';') if p.lower().startswith((sysroot.lower(), r'c:\program files'))]
    env = {'SystemRoot': sysroot, 'windir': sysroot, 'ComSpec': os.path.join(sysroot, 'System32', 'cmd.exe'),
           'PATH': ';'.join(path), 'PATHEXT': '.COM;.EXE;.BAT;.CMD', 'TEMP': str(tmp), 'TMP': str(tmp),
           'USERPROFILE': str(home), 'HOME': str(home), 'NUMBER_OF_PROCESSORS': os.environ.get('NUMBER_OF_PROCESSORS', '2'),
           'PROCESSOR_ARCHITECTURE': os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64'),
           # required by CreateProcess for AppContainers (error 203 without it); Windows rewrites LOCALAPPDATA/TEMP/TMP
           # to the container's own folder %LOCALAPPDATA%\Packages\ma.jarvis.pcworker\AC
           'LOCALAPPDATA': os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))}
    env.update(extra or {})
    return env


class Sandbox:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('winsandbox läuft nur unter Windows')
        self.sid = container_sid()

    def run(self, argv: list[str], work: Path, limits: Limits | None = None, env: dict | None = None) -> Result:
        lim = limits or Limits()
        work = Path(work).resolve()
        exe = shutil.which(argv[0], path=(env or base_env(work))['PATH']) or argv[0]
        argv = [exe, *argv[1:]]
        log_path = work.parent / f'out-{os.getpid()}-{time.monotonic_ns()}.log'
        sa = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
        h_out = k32.CreateFileW(str(log_path), GENERIC_WRITE, FILE_SHARE_RW, ctypes.byref(sa), CREATE_ALWAYS, 0, None)
        _check(h_out not in (None, INVALID), 'CreateFile log')
        h_in = k32.CreateFileW('NUL', GENERIC_READ, FILE_SHARE_RW, ctypes.byref(sa), OPEN_EXISTING, 0, None)
        _check(h_in not in (None, INVALID), 'CreateFile NUL')
        job = pi = None
        cont = _sid_from_string(self.sid)
        cap_sids = [_sid_from_string(capability_sid(VOLUME_ROOT_CAP))]
        if lim.network:
            cap_sids.append(_sid_from_string(INTERNET_CLIENT_SID))
        try:
            # --- job object with limits (created first, process is assigned while still suspended)
            job = k32.CreateJobObjectW(None, None)
            _check(job, 'CreateJobObject')
            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = (JOB_OBJECT_LIMIT_ACTIVE_PROCESS | JOB_OBJECT_LIMIT_JOB_MEMORY
                                                     | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_PRIORITY_CLASS
                                                     | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION)
            info.BasicLimitInformation.ActiveProcessLimit = lim.procs
            info.BasicLimitInformation.PriorityClass = BELOW_NORMAL_PRIORITY_CLASS
            info.JobMemoryLimit = lim.mem_mb * 1024 * 1024
            _check(k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)),
                   'SetInformationJobObject limits')
            cpu = JOBOBJECT_CPU_RATE_CONTROL_INFORMATION(JOB_OBJECT_CPU_RATE_CONTROL_ENABLE | JOB_OBJECT_CPU_RATE_CONTROL_HARD_CAP,
                                                         max(1, min(100, lim.cpu_pct)) * 100)
            _check(k32.SetInformationJobObject(job, JobObjectCpuRateControlInformation, ctypes.byref(cpu), ctypes.sizeof(cpu)),
                   'SetInformationJobObject cpu')
            ui = wt.DWORD(JOB_OBJECT_UILIMIT_ALL)
            _check(k32.SetInformationJobObject(job, JobObjectBasicUIRestrictions, ctypes.byref(ui), ctypes.sizeof(ui)),
                   'SetInformationJobObject ui')

            # --- attribute list: AppContainer + only our two std handles are inheritable
            caps = (SID_AND_ATTRIBUTES * len(cap_sids))(*[SID_AND_ATTRIBUTES(c.value, SE_GROUP_ENABLED) for c in cap_sids])
            sc = SECURITY_CAPABILITIES(cont.value, caps, len(cap_sids), 0)
            handles = (wt.HANDLE * 2)(h_out, h_in)
            size = ctypes.c_size_t()
            k32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
            attr = ctypes.create_string_buffer(size.value)
            _check(k32.InitializeProcThreadAttributeList(attr, 2, 0, ctypes.byref(size)), 'InitializeProcThreadAttributeList')
            _check(k32.UpdateProcThreadAttribute(attr, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES, ctypes.byref(sc),
                                                 ctypes.sizeof(sc), None, None), 'UpdateProcThreadAttribute caps')
            _check(k32.UpdateProcThreadAttribute(attr, 0, PROC_THREAD_ATTRIBUTE_HANDLE_LIST, ctypes.cast(handles, ctypes.c_void_p),
                                                 ctypes.sizeof(handles), None, None), 'UpdateProcThreadAttribute handles')
            si = STARTUPINFOEXW()
            si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
            si.StartupInfo.dwFlags = STARTF_USESTDHANDLES
            si.StartupInfo.hStdInput, si.StartupInfo.hStdOutput, si.StartupInfo.hStdError = h_in, h_out, h_out
            si.lpAttributeList = ctypes.cast(attr, ctypes.c_void_p)
            pi = PROCESS_INFORMATION()
            cmd = ctypes.create_unicode_buffer(_cmdline(argv))
            envb = _env_block(env or base_env(work))
            t0 = time.monotonic()
            ok = k32.CreateProcessW(None, cmd, None, None, True,
                                    EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT
                                    | CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS,
                                    ctypes.cast(envb, ctypes.c_void_p), str(work), ctypes.byref(si), ctypes.byref(pi))
            err = ctypes.get_last_error()
            k32.DeleteProcThreadAttributeList(attr)
            if not ok:
                raise ctypes.WinError(err, f'CreateProcess {argv[0]}')
            if not k32.AssignProcessToJobObject(job, pi.hProcess):
                err = ctypes.get_last_error()
                k32.TerminateProcess(pi.hProcess, 1)
                raise ctypes.WinError(err, 'AssignProcessToJobObject')
            k32.ResumeThread(pi.hThread)
            timed_out = k32.WaitForSingleObject(pi.hProcess, int(lim.timeout_s * 1000)) == WAIT_TIMEOUT
            code = wt.DWORD()
            if timed_out:
                k32.TerminateJobObject(job, 124)
                k32.WaitForSingleObject(pi.hProcess, 10000)
                code.value = 124
            else:
                k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
            secs = time.monotonic() - t0
            k32.QueryInformationJobObject(job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info), None)
            acc = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            k32.QueryInformationJobObject(job, JobObjectBasicAccountingInformation, ctypes.byref(acc), ctypes.sizeof(acc), None)
            k32.TerminateJobObject(job, 1)  # leftovers (e.g. a Gradle daemon) never outlive the step
            left = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            for _ in range(200):  # termination is asynchronous: wait until the tree is really gone (max 10 s)
                k32.QueryInformationJobObject(job, JobObjectBasicAccountingInformation, ctypes.byref(left),
                                              ctypes.sizeof(left), None)
                if left.ActiveProcesses == 0:
                    break
                time.sleep(0.05)
        finally:
            for h in (h_out, h_in):
                k32.CloseHandle(h)
            if pi is not None:
                k32.CloseHandle(pi.hThread)
                k32.CloseHandle(pi.hProcess)
            if job:
                k32.CloseHandle(job)
            k32.LocalFree(cont)
            for c in cap_sids:
                k32.LocalFree(c)
        out = log_path.read_bytes().decode('utf-8', errors='replace')
        for _ in range(100):  # handles of killed processes are closed a moment after the job reports 0 processes
            try:
                log_path.unlink(missing_ok=True)
                break
            except PermissionError:
                time.sleep(0.05)
        return Result(code=code.value if code.value < 0x80000000 else code.value - 0x100000000, output=out[-20000:],
                      timed_out=timed_out, seconds=round(secs, 2),
                      peak_mem_mb=round(info.PeakJobMemoryUsed / 1048576, 1), processes=acc.TotalProcesses,
                      info={'container_sid': self.sid,
                            'capabilities': [VOLUME_ROOT_CAP] + (['internetClient'] if lim.network else []),
                            'network': lim.network, 'mem_mb': lim.mem_mb, 'procs': lim.procs,
                            'cpu_pct': lim.cpu_pct, 'timeout_s': lim.timeout_s})


def cleanup(work: Path) -> None:
    """Remove a step folder created by new_workdir (only below ROOT)."""
    d = Path(work).resolve().parent
    if ROOT.resolve() in d.parents:
        shutil.rmtree(d, ignore_errors=True)
