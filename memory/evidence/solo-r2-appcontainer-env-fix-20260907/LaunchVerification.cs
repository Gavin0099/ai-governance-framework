using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Security.Principal;
public static class LaunchDiagnosis {
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct Caps {public IntPtr Sid, Capabilities; public uint Count,Reserved;}
 [StructLayout(LayoutKind.Sequential,Pack=8,CharSet=CharSet.Unicode)] struct Startup {
  public int cb; public IntPtr reserved,desktop,title; public uint x,y,xs,ys,xc,yc,fill,flags;
  public ushort show,cbReserved; public IntPtr reserved2,input,output,error;
 }
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct StartupEx { public Startup si; public IntPtr attrs; }
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct Proc {public IntPtr process,thread;public uint pid,tid;}
 [DllImport("C:\\Windows\\System32\\userenv.dll",CharSet=CharSet.Unicode,CallingConvention=CallingConvention.Winapi)]
 static extern int DeriveAppContainerSidFromAppContainerName(string name,out IntPtr sid);
 [DllImport("C:\\Windows\\System32\\advapi32.dll",CallingConvention=CallingConvention.Winapi)] static extern IntPtr FreeSid(IntPtr sid);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,int flags,ref IntPtr size);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr attr,IntPtr value,IntPtr size,IntPtr previous,IntPtr result);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CallingConvention=CallingConvention.Winapi)] static extern void DeleteProcThreadAttributeList(IntPtr list);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool CreateProcessW(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref StartupEx start,out Proc proc);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CallingConvention=CallingConvention.Winapi)] static extern uint WaitForSingleObject(IntPtr h,uint ms);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)] static extern bool GetExitCodeProcess(IntPtr h,out uint code);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CallingConvention=CallingConvention.Winapi)] static extern bool TerminateProcess(IntPtr h,uint code);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CallingConvention=CallingConvention.Winapi)] static extern bool CloseHandle(IntPtr h);
 [DllImport("C:\\Windows\\System32\\advapi32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
 [DllImport("C:\\Windows\\System32\\advapi32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr buffer,int size,out int needed);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern IntPtr CreateFileW(string path,uint access,uint share,IntPtr sa,uint disposition,uint flags,IntPtr template);

 public static string Run(bool container,bool inherit,string environment,string executable,string command,string cwd) {
  if(Environment.OSVersion.Platform!=PlatformID.Win32NT || !Environment.Is64BitProcess || Marshal.SizeOf(typeof(StartupEx))!=112)throw new Exception("Unsupported ABI");
  if(executable!=@"D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1\Probe.exe" && executable!=@"C:\Windows\System32\cmd.exe")throw new Exception("Fixed target required");
  IntPtr sid=IntPtr.Zero,attrs=IntPtr.Zero,cap=IntPtr.Zero,env=IntPtr.Zero;Proc pi=new Proc();bool initialized=false;
  try {
   StartupEx si=new StartupEx();uint flags=0x08000404; // NO_WINDOW | UNICODE_ENVIRONMENT | SUSPENDED
   si.si.cb=Marshal.SizeOf(typeof(Startup));
   string sidText="none";
   if(container){
    int hr=DeriveAppContainerSidFromAppContainerName("SoloR2.Final.74ad1963.Scoring1",out sid);if(hr!=0)return "derive_hresult="+hr;
    sidText=new SecurityIdentifier(sid).Value;
    IntPtr size=IntPtr.Zero;InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);if(size==IntPtr.Zero)return "attribute_size_error="+Marshal.GetLastWin32Error();
    attrs=Marshal.AllocHGlobal(size);if(!InitializeProcThreadAttributeList(attrs,1,0,ref size))return "attribute_init_error="+Marshal.GetLastWin32Error();initialized=true;
    cap=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Caps)));Marshal.StructureToPtr(new Caps{Sid=sid},cap,false);
    if(!UpdateProcThreadAttribute(attrs,0,new IntPtr(0x20009),cap,new IntPtr(Marshal.SizeOf(typeof(Caps))),IntPtr.Zero,IntPtr.Zero))return "attribute_update_error="+Marshal.GetLastWin32Error();
    si.si.cb=Marshal.SizeOf(typeof(StartupEx));si.attrs=attrs;flags|=0x80000;
   }
   if(!inherit){
    if(environment==null || !environment.EndsWith("\0\0"))throw new Exception("Bad environment terminator");
    env=Marshal.StringToHGlobalUni(environment);
    byte[] actual=new byte[environment.Length*2];Marshal.Copy(env,actual,0,actual.Length);
    if(Encoding.Unicode.GetString(actual)!=environment)throw new Exception("Environment memory mismatch");
   }
   bool ok=CreateProcessW(executable,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,false,flags,env,cwd,ref si,out pi);
   int error=ok?0:Marshal.GetLastWin32Error();
   // Never resume: the original --child filesystem probe cannot execute.
   if(!ok)return "create_error="+error+";sid="+sidText;
   IntPtr tok=IntPtr.Zero,buf=Marshal.AllocHGlobal(4096);int needed;int app=-1;string actualSid="none";
   try{if(!OpenProcessToken(pi.process,8,out tok))throw new Exception("Token open error");if(!GetTokenInformation(tok,29,buf,4096,out needed))throw new Exception("Token query error");app=Marshal.ReadInt32(buf);if(app==1){if(!GetTokenInformation(tok,31,buf,4096,out needed))throw new Exception("AppContainer SID query error");actualSid=new SecurityIdentifier(Marshal.ReadIntPtr(buf)).Value;if(actualSid!=sidText || actualSid!="S-1-15-2-131220624-4122180277-3555119406-1414502418-3096179838-1091309190-3293210637")throw new Exception("Actual token SID mismatch");}}
   finally{if(tok!=IntPtr.Zero)CloseHandle(tok);Marshal.FreeHGlobal(buf);}
   if(!TerminateProcess(pi.process,0))throw new Exception("Terminate suspended child failed");
   if(WaitForSingleObject(pi.process,5000)!=0)throw new Exception("Child exit wait failed");
   return "created_suspended=true;token_is_appcontainer="+app+";terminated_without_resume=true;actual_token_sid="+actualSid+";sid="+sidText;
  } finally {
   if(pi.process!=IntPtr.Zero){TerminateProcess(pi.process,0);WaitForSingleObject(pi.process,5000);CloseHandle(pi.process);}
   if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);
   if(env!=IntPtr.Zero)Marshal.FreeHGlobal(env);if(cap!=IntPtr.Zero)Marshal.FreeHGlobal(cap);
   if(initialized)DeleteProcThreadAttributeList(attrs);if(attrs!=IntPtr.Zero)Marshal.FreeHGlobal(attrs);if(sid!=IntPtr.Zero)FreeSid(sid);
  }
 }
}
