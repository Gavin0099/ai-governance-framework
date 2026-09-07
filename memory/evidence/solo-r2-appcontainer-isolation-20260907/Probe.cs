// Fixed, non-scoring AppContainer probe. No model, network, or bundle generation.
// Win32 UTF-16 parameters are copied/used synchronously; native allocations are
// released by their paired APIs. All raw handles stay in this adapter.
using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Principal;

internal static class Probe {
 const string Name = "SoloR2.Final.74ad1963.Scoring1";
 const string Root = @"D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1";
 const string Canary = "{\"kind\":\"SYNTHETIC_ONLY\",\"correctness\":{\"passed\":10,\"required\":10},\"summary\":\"Synthetic projection; no arm output.\"}\n";
 // This executable is probe-only; its AppContainer read/execute ACL is revoked
 // after the probe. It must NEVER be included in a later scorer input delivery.
 static readonly string[] Forbidden = {
  @"D:\ai-governance-framework\AGENTS.md",
  @"D:\ai-governance-framework\.git\config",
  @"D:\r2-final-disposable-shakedown-20260907\scoring\2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.blind-scoring-bundle.json",
  @"D:\r2-final-disposable-shakedown-20260907\controller\2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.scoring-bound.sealed.json",
  @"D:\r2-final-disposable-shakedown-20260907\keys\controller-key.json",
  @"D:\ai-governance-framework\memory\2026-09-07.md",
  @"D:\ai-governance-framework\memory\evidence\solo-r2-final-scoring-continuation-adoption-20260907\owner-adoption.json",
  @"D:\ai-governance-framework\artifacts\evidence\solo-r2-final-disposable-mechanism-shakedown-20260907\attempt-ledger.v2.1.ndjson"
 };
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct Caps {public IntPtr Sid, Capabilities; public uint Count,Reserved;}
 [StructLayout(LayoutKind.Sequential,Pack=8,CharSet=CharSet.Unicode)] struct Startup {
  public int cb; public IntPtr reserved,desktop,title; public uint x,y,xs,ys,xc,yc,fill,flags;
  public ushort show,cbReserved; public IntPtr reserved2,input,output,error;
 }
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct StartupEx { public Startup si; public IntPtr attrs; }
 [StructLayout(LayoutKind.Sequential,Pack=8)] struct Proc {public IntPtr process,thread;public uint pid,tid;}
 [DllImport("C:\\Windows\\System32\\userenv.dll",CharSet=CharSet.Unicode,CallingConvention=CallingConvention.Winapi)]
 static extern int CreateAppContainerProfile(string name,string display,string description,IntPtr capabilities,uint count,out IntPtr sid);
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
 static void Check(bool b){if(!b)throw new Win32Exception(Marshal.GetLastWin32Error());}
 static bool Denied(string path,uint access) {
  IntPtr h=CreateFileW(path,access,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero);
  if(h!=new IntPtr(-1)){CloseHandle(h);return false;}
  return Marshal.GetLastWin32Error()==5;
 }
 static bool TokenMatches() {
  IntPtr token=IntPtr.Zero,buf=Marshal.AllocHGlobal(4096),sid=IntPtr.Zero;
  try {
   Check(OpenProcessToken(Process.GetCurrentProcess().Handle,8,out token));int n;
   Check(GetTokenInformation(token,29,buf,4096,out n));if(Marshal.ReadInt32(buf)!=1)return false;
   Check(GetTokenInformation(token,30,buf,4096,out n));if(Marshal.ReadInt32(buf)!=0)return false;
   Check(GetTokenInformation(token,31,buf,4096,out n));string actual=new SecurityIdentifier(Marshal.ReadIntPtr(buf)).Value;
   int hr=DeriveAppContainerSidFromAppContainerName(Name,out sid);if(hr!=0)Marshal.ThrowExceptionForHR(hr);
   return actual==new SecurityIdentifier(sid).Value;
  } finally {if(sid!=IntPtr.Zero)FreeSid(sid);if(token!=IntPtr.Zero)CloseHandle(token);Marshal.FreeHGlobal(buf);}
 }
 static int Child() {
  int mask=0;
  if(TokenMatches())mask|=1;
  // Real OS read + exact synthetic projection verification. Never real outputs.
  if(File.ReadAllText(Root+@"\inputs\projection.json",Encoding.UTF8)==Canary)mask|=2;
  if(Denied(Root+@"\inputs\projection.json",0x40000000))mask|=4;
  for(int i=0;i<Forbidden.Length;i++)if(Denied(Forbidden[i],0x80000000))mask|=1<<(i+3);
  return mask;
 }
 static uint Launch() {
  foreach(string p in Forbidden)if(!File.Exists(p))throw new Exception("Forbidden target absent; cannot claim denial");
  IntPtr sid=IntPtr.Zero,attrs=IntPtr.Zero,cap=IntPtr.Zero,env=IntPtr.Zero;Proc pinfo=new Proc();bool initialized=false;
  try {
   int hr=DeriveAppContainerSidFromAppContainerName(Name,out sid);if(hr!=0)Marshal.ThrowExceptionForHR(hr);
   IntPtr size=IntPtr.Zero;InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
   if(size==IntPtr.Zero)throw new Exception("No attribute buffer size");attrs=Marshal.AllocHGlobal(size);
   Check(InitializeProcThreadAttributeList(attrs,1,0,ref size));initialized=true;
   cap=Marshal.AllocHGlobal(Marshal.SizeOf(typeof(Caps)));Marshal.StructureToPtr(new Caps{Sid=sid},cap,false);
   Check(UpdateProcThreadAttribute(attrs,0,new IntPtr(0x20009),cap,new IntPtr(Marshal.SizeOf(typeof(Caps))),IntPtr.Zero,IntPtr.Zero));
   StartupEx si=new StartupEx();si.si.cb=Marshal.SizeOf(typeof(StartupEx));si.attrs=attrs;
   // No inherited handles, environment selectors, network capabilities or model.
   env=Marshal.StringToHGlobalUni("LOCALAPPDATA=C:\\Users\\daish\\AppData\\Local\0SystemRoot=C:\\Windows\0WINDIR=C:\\Windows\0\0");
   string exe=Root+@"\Probe.exe";
   Check(CreateProcessW(exe,new StringBuilder("\""+exe+"\" --child"),IntPtr.Zero,IntPtr.Zero,false,0x08080400,env,Root+@"\inputs",ref si,out pinfo));
   if(WaitForSingleObject(pinfo.process,30000)!=0){TerminateProcess(pinfo.process,255);WaitForSingleObject(pinfo.process,5000);throw new Exception("Probe timed out");}
   uint code;Check(GetExitCodeProcess(pinfo.process,out code));return code;
  } finally {
   if(pinfo.thread!=IntPtr.Zero)CloseHandle(pinfo.thread);if(pinfo.process!=IntPtr.Zero)CloseHandle(pinfo.process);
   if(env!=IntPtr.Zero)Marshal.FreeHGlobal(env);if(cap!=IntPtr.Zero)Marshal.FreeHGlobal(cap);
   if(initialized)DeleteProcThreadAttributeList(attrs);if(attrs!=IntPtr.Zero)Marshal.FreeHGlobal(attrs);if(sid!=IntPtr.Zero)FreeSid(sid);
  }
 }
 static int Main(string[] args) {
  try {
   if(Environment.OSVersion.Platform!=PlatformID.Win32NT || !Environment.Is64BitProcess || Marshal.SizeOf(typeof(StartupEx))!=112 || Marshal.SizeOf(typeof(Caps))!=24)throw new Exception("Unsupported ABI");
   if(args.Length!=1)throw new Exception("Fixed mode required");
   if(args[0]=="--child")return Child();
   if(args[0]=="--create") {
    IntPtr sid=IntPtr.Zero;
    try{int hr=CreateAppContainerProfile(Name,Name,"Solo R2 non-scoring isolation probe",IntPtr.Zero,0,out sid);if(hr!=0)Marshal.ThrowExceptionForHR(hr);Console.WriteLine(new SecurityIdentifier(sid).Value);}
    finally{if(sid!=IntPtr.Zero)FreeSid(sid);}return 0;
   }
   if(args[0]=="--probe") {uint result=Launch();Console.WriteLine(result);return result==2047?0:1;}
   throw new Exception("Unknown mode");
  } catch(Exception e){Console.Error.WriteLine(e.GetType().Name+": "+e.Message);return 255;}
 }
}
