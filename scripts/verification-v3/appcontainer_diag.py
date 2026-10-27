"""Read-only-ish diagnosis of AppContainer creation: creates ONE uniquely named test profile and deletes it again."""
import ctypes,uuid
from ctypes import wintypes
u=ctypes.WinDLL('userenv'); k=ctypes.WinDLL('kernel32')
sid=ctypes.c_void_p(); name='mahome.diag.'+uuid.uuid4().hex[:8]
hr=u.CreateAppContainerProfile(name,name,name,None,0,ctypes.byref(sid))
print('CreateAppContainerProfile hr=0x%08X'%(hr&0xFFFFFFFF))
if hr==0:
    print('DeleteAppContainerProfile hr=0x%08X'%(u.DeleteAppContainerProfile(name)&0xFFFFFFFF))
inj=wintypes.BOOL(); k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(inj)); print('in_job',bool(inj.value))
