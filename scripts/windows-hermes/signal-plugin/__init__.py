"""Reuse upstream Signal lifecycle/echo filtering, narrow intake and encode remote media."""
from plugins.platforms.signal.adapter import SignalAdapter
from plugins.platforms.signal.register import register as upstream_register
from .policy import is_owner_note,remote_params

class SelfOnlySignalAdapter(SignalAdapter):
 async def _handle_envelope(self,envelope):
  if not is_owner_note(envelope,self.account):return
  await super()._handle_envelope(envelope)
 async def _rpc(self,method,params,*args,**kwargs):
  return await super()._rpc(method,remote_params(method,params),*args,**kwargs)

def register(ctx):
 class RegistrationProxy:
  def register_platform(self,**kwargs):
   kwargs['adapter_factory']=SelfOnlySignalAdapter
   kwargs['platform_hint']+=' Respond conversationally in German. Prefer concise text; use text_to_speech when the owner requests an audio reply. Never read or act on other private chats.'
   ctx.register_platform(**kwargs)
 upstream_register(RegistrationProxy())
