"""Windows-only owned audit-store leases. Legacy token-only locks are never stolen."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
import ctypes,ctypes.wintypes as w,hashlib,json,os,uuid,winreg

def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
def publish(path,data):
    """Publish a complete file without replacement; interrupted stages remain as evidence."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('append_only_target_conflict: '+str(path))
        return False
    stage=path.parent/('.'+path.name+'.pending-'+str(uuid.uuid4()))
    with stage.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    try:os.link(stage,path)  # no replace; destination becomes visible only after complete write
    except FileExistsError:
        if path.read_bytes()!=data:raise
    stage.unlink()  # only this operation's staging link; published bytes remain
    return True

def kernel():
    if os.name!='nt':raise RuntimeError('Windows process ownership API required')
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    signatures={
      'CreateMutexW':([ctypes.c_void_p,w.BOOL,w.LPCWSTR],w.HANDLE),
      'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
      'ReleaseMutex':([w.HANDLE],w.BOOL),'CloseHandle':([w.HANDLE],w.BOOL),
      'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
      'K32EnumProcesses':([ctypes.POINTER(w.DWORD),w.DWORD,ctypes.POINTER(w.DWORD)],w.BOOL),
      'GetVolumePathNameW':([w.LPCWSTR,w.LPWSTR,w.DWORD],w.BOOL),
      'GetDriveTypeW':([w.LPCWSTR],w.UINT),
      'GetVolumeInformationW':([w.LPCWSTR,w.LPWSTR,w.DWORD,ctypes.POINTER(w.DWORD),ctypes.POINTER(w.DWORD),ctypes.POINTER(w.DWORD),w.LPWSTR,w.DWORD],w.BOOL),
      'GetProcessTimes':([w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)],w.BOOL)}
    for name,(args,result) in signatures.items():getattr(k,name).argtypes=args;getattr(k,name).restype=result
    return k

def machine_id():
    # Local installation binding, not authentication; cloning this OS/store is unsupported.
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography',0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
        value,kind=winreg.QueryValueEx(key,'MachineGuid')
    if not isinstance(value,str) or not value.strip():raise RuntimeError('machine_identity_unavailable')
    return sha(value.strip().lower().encode())

def filesystem(root):
    k=kernel();volume=ctypes.create_unicode_buffer(32768);fs=ctypes.create_unicode_buffer(256);flags=w.DWORD()
    if not k.GetVolumePathNameW(str(Path(root).resolve()),volume,len(volume)):raise ctypes.WinError(ctypes.get_last_error())
    drive=k.GetDriveTypeW(volume.value)
    if not k.GetVolumeInformationW(volume.value,None,0,None,None,ctypes.byref(flags),fs,len(fs)):raise ctypes.WinError(ctypes.get_last_error())
    if drive!=3 or fs.value!='NTFS' or not flags.value&0x00400000:raise RuntimeError('requires_local_fixed_NTFS_with_hardlinks')
    return {'drive_type':drive,'filesystem':fs.value,'hardlinks_supported':True}

def process_state(pid):
    if type(pid) is not int or pid<=0 or pid>0xffffffff:raise ValueError('invalid_owner_pid')
    k=kernel();h=k.OpenProcess(0x1000|0x100000,False,pid)
    if not h:
        error=ctypes.get_last_error()
        if error==87:
            # Error alone is insufficient: confirm absence from a complete process list.
            size=1024
            while size<=1048576:
                pids=(w.DWORD*size)();used=w.DWORD()
                if not k.K32EnumProcesses(pids,ctypes.sizeof(pids),ctypes.byref(used)):raise ctypes.WinError(ctypes.get_last_error())
                if used.value<ctypes.sizeof(pids):
                    if pid in pids[:used.value//ctypes.sizeof(w.DWORD)]:raise RuntimeError('owner_pid_exists_but_cannot_open')
                    return {'state':'absent','pid':pid,'winerror':error,'absence_confirmed_by':'K32EnumProcesses'}
                size*=2
            raise RuntimeError('process_inventory_incomplete')
        raise OSError(error,'Process ownership unavailable; cannot infer death')
    try:
        created,exited,krn,usr=(w.FILETIME() for _ in range(4))
        if not k.GetProcessTimes(h,ctypes.byref(created),ctypes.byref(exited),ctypes.byref(krn),ctypes.byref(usr)):raise ctypes.WinError(ctypes.get_last_error())
        wait=k.WaitForSingleObject(h,0)
        if wait not in [0,258]:raise RuntimeError('process_wait_unknown')
        return {'pid':pid,'creation_filetime':str((created.dwHighDateTime<<32)|created.dwLowDateTime),'state':'terminated' if wait==0 else 'running'}
    finally:k.CloseHandle(h)

@contextmanager
def named_mutex(name):
    k=kernel()
    h=k.CreateMutexW(None,False,name)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    acquired=False
    try:
        result=k.WaitForSingleObject(h,0)
        if result not in [0,128]:raise RuntimeError('audit_store_mutex_busy_or_unavailable')
        acquired=True;yield {'abandoned':result==128}
    finally:
        if acquired:k.ReleaseMutex(h)
        k.CloseHandle(h)

@contextmanager
def mutex(root):
    store=json.loads((Path(root)/'STORE.json').read_text(encoding='utf-8-sig'))
    identifier=str(uuid.UUID(store['store_id']))
    with named_mutex('Global\\LAT_AI_AUDIT_'+identifier) as state:yield state

def lock_status(root):
    root=Path(root).resolve();lock=root/'intake.lock'
    barrier=root/'recovery/BARRIER.json'
    if barrier.exists():
        binding=json.loads(barrier.read_text(encoding='utf-8'))
        store=json.loads((root/'STORE.json').read_text(encoding='utf-8-sig'))
        if binding.get('store_id')!=store['store_id'] or binding.get('role')!='persistent_legacy_writer_barrier':raise ValueError('barrier_binding_mismatch')
        if binding.get('machine_id_sha256')!=machine_id():return {'state':'foreign_or_unknown_host'}
    if not lock.exists():return {'state':'missing_initialized_barrier' if barrier.exists() else 'unlocked'}
    raw=lock.read_bytes()
    try:
        token=raw.decode('ascii');parsed=uuid.UUID(token)
        if str(parsed)!=token or parsed.version!=4:raise ValueError()
    except (ValueError,UnicodeError):return {'state':'legacy_or_unknown','lock_sha256':sha(raw)}
    folder=root/'recovery/leases';metadata=folder/(token+'.json');tokenfile=folder/(token+'.token')
    if not metadata.exists() or not tokenfile.exists():return {'state':'legacy_or_unknown','lock_sha256':sha(raw),'token':token}
    owner=json.loads(metadata.read_text(encoding='utf-8'))
    if owner.get('token')!=token or owner.get('store_path')!=str(root) or tokenfile.read_bytes()!=raw:raise ValueError('owner_metadata_mismatch')
    store=json.loads((root/'STORE.json').read_text(encoding='utf-8-sig'))
    if owner.get('store_id')!=store['store_id']:raise ValueError('owner_store_mismatch')
    if owner.get('machine_id_sha256')!=machine_id():return {'state':'foreign_or_unknown_host','lock_sha256':sha(raw),'token':token}
    released=folder/(token+'.released.json')
    if released.exists():
        release=json.loads(released.read_text(encoding='utf-8'))
        if set(release)!={'released_utc','owner'} or release['owner']!=token:raise ValueError('release_record_mismatch')
        datetime.fromisoformat(release['released_utc'])
        return {'state':'owned_idle_barrier','token':token,'owner':owner,'lock_sha256':sha(raw)}
    actual=process_state(owner['pid'])
    dead=actual['state'] in ['absent','terminated'] or actual.get('creation_filetime')!=owner['creation_filetime']
    return {'state':'owned_dead' if dead else 'owned_running','token':token,'owner':owner,'actual_process':actual,'lock_sha256':sha(raw)}

def exchange_stage_status(root,path):
    """Recognize our retained pre-exchange hardlink; never remove it automatically."""
    root=Path(root).resolve();path=Path(path)
    if not path.name.startswith('.intake.lock.next-'):return None
    token=path.name[len('.intake.lock.next-'):]
    parsed=uuid.UUID(token)
    if str(parsed)!=token or parsed.version!=4:raise ValueError('invalid_exchange_stage_token')
    folder=root/'recovery/leases';owner=json.loads((folder/(token+'.json')).read_text(encoding='utf-8'))
    if path.read_bytes()!=token.encode() or (folder/(token+'.token')).read_bytes()!=token.encode() or owner['token']!=token or owner['store_path']!=str(root) or owner['machine_id_sha256']!=machine_id():raise ValueError('unknown_exchange_stage')
    return {'kind':'owned_lease_exchange_stage_preserved','token':token}

@contextmanager
def owned_lease(root,protocol_sha):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    fs=filesystem(root);host=machine_id()
    # One bootstrap mutex serializes first STORE publication even through path aliases.
    with named_mutex('Global\\LAT_AI_AUDIT_BOOTSTRAP'):
        if not (root/'STORE.json').exists():publish(root/'STORE.json',encoded({'store_id':str(uuid.uuid4()),'scope':'Single coordinated audit store'}))
        hostfile=root/'recovery/HOST.json';binding={'machine_id_sha256':host,'store_id':json.loads((root/'STORE.json').read_text(encoding='utf-8-sig'))['store_id']}
        publish(hostfile,encoded(binding))
    with mutex(root) as mutex_state:
        status=lock_status(root)
        if status['state'] not in ['unlocked','owned_dead','owned_idle_barrier']:raise RuntimeError('lock_not_recoverable: '+status['state'])
        if status['state']=='owned_dead':
            # Kernel mutex serializes all new lease owners. V1 cannot reserve while lock exists.
            old=root/'intake.lock';archive=root/'recovery/leases'/(status['token']+'.retired-token')
            publish(archive,old.read_bytes())
            proof=root/'recovery/leases'/(status['token']+'.death-proof.json')
            if not proof.exists():publish(proof,encoded({'observed_utc':datetime.now(timezone.utc).isoformat(),'proof':status}))
            else:
                prior=json.loads(proof.read_text(encoding='utf-8'))['proof']
                if prior['state']!='owned_dead' or prior['token']!=status['token'] or prior['lock_sha256']!=status['lock_sha256'] or prior['owner']!=status['owner']:raise ValueError('death_proof_mismatch')
            if sha(old.read_bytes())!=status['lock_sha256']:raise ValueError('lock_changed_during_retirement')
        token=str(uuid.uuid4());owner=process_state(os.getpid())
        if owner['state']!='running':raise RuntimeError('current_process_identity_unavailable')
        folder=root/'recovery/leases';folder.mkdir(parents=True,exist_ok=True)
        record={**owner,'token':token,'store_path':str(root),'store_id':binding['store_id'],'machine_id_sha256':host,'filesystem':fs,'mutex_abandoned':mutex_state['abandoned'],'protocol_sha256':protocol_sha,'created_utc':datetime.now(timezone.utc).isoformat()}
        publish(folder/(token+'.json'),encoded(record));publish(folder/(token+'.token'),token.encode('ascii'))
        publish(root/'recovery/BARRIER.json',encoded({**binding,'role':'persistent_legacy_writer_barrier'}))
        lock=root/'intake.lock'
        if status['state']=='unlocked':os.link(folder/(token+'.token'),lock)
        else:
            # No absent-lock gap: legacy v1 always sees FileExistsError, even while idle.
            # The previous token remains in its immutable .token and lease/death records.
            if sha(lock.read_bytes())!=status['lock_sha256']:raise ValueError('lock_changed_before_exchange')
            stage=root/('.intake.lock.next-'+token);os.link(folder/(token+'.token'),stage)
            os.replace(stage,lock)
        try:yield root
        finally:
            lock=root/'intake.lock'
            if lock.read_bytes()!=token.encode('ascii'):raise RuntimeError('owned_lock_changed')
            publish(folder/(token+'.released.json'),encoded({'released_utc':datetime.now(timezone.utc).isoformat(),'owner':token}))
            # Persistent, released barrier deliberately excludes unaware legacy writers.
