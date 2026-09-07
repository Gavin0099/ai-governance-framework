// Fixed Solo R2 Windows adapter. Compiled into the probe; never scorer delivery.
// These are OS custody and exact reviewed-projection delivery verifiers, not a
// semantic-review engine. expectedReviewedSha256 must originate outside the
// inspected file; real projection semantic review remains a caller prerequisite.
using System;
using System.IO;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Diagnostics;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class SoloR2ScoringHostVerifiers {
 public const string Root = @"D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1";
 public const string Projection = Root+@"\inputs\projection.json";
 const string Owner = "S-1-5-21-4017902291-1272973841-664929404-1001";
 const string App = "S-1-15-2-131220624-4122180277-3555119406-1414502418-3096179838-1091309190-3293210637";
 // Existing probe targets only. Opening checks permissions, never reads bytes.
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
 [StructLayout(LayoutKind.Sequential,Pack=4)] struct FileIdentity {
  public uint Attributes,CreateLow,CreateHigh,AccessLow,AccessHigh,WriteLow,WriteHigh;
  public uint Volume,SizeHigh,SizeLow,Links,IndexHigh,IndexLow;
 }
 [DllImport("C:\\Windows\\System32\\kernel32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool GetFileInformationByHandle(SafeFileHandle file,out FileIdentity info);
 [DllImport("C:\\Windows\\System32\\advapi32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
 [DllImport("C:\\Windows\\System32\\advapi32.dll",SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern bool GetTokenInformation(IntPtr token,int kind,IntPtr buffer,int size,out int needed);
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CallingConvention=CallingConvention.Winapi)]
 static extern bool CloseHandle(IntPtr handle);
 // Win32 explicitly requires UTF-16; path pointer used synchronously only.
 [DllImport("C:\\Windows\\System32\\kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true,CallingConvention=CallingConvention.Winapi)]
 static extern SafeFileHandle CreateFileW(string path,uint access,uint share,IntPtr sa,uint disposition,uint flags,IntPtr template);
 static void Require(bool value){if(!value)throw new InvalidOperationException("SCORING_HOST_VERIFICATION_REJECTED");}
 static void Token(){
  Require(Environment.OSVersion.Platform==PlatformID.Win32NT && Environment.Is64BitProcess && Marshal.SizeOf(typeof(FileIdentity))==52);
  IntPtr token=IntPtr.Zero,buf=Marshal.AllocHGlobal(4096);
  try {
   using(var process=Process.GetCurrentProcess()){Require(OpenProcessToken(process.Handle,8,out token));}
   int needed;Require(GetTokenInformation(token,29,buf,4096,out needed));Require(Marshal.ReadInt32(buf)==1);
   Require(GetTokenInformation(token,30,buf,4096,out needed));Require(Marshal.ReadInt32(buf)==0);
   Require(GetTokenInformation(token,31,buf,4096,out needed));Require(new SecurityIdentifier(Marshal.ReadIntPtr(buf)).Value==App);
  } finally {if(token!=IntPtr.Zero)CloseHandle(token);Marshal.FreeHGlobal(buf);}
 }
 static void NoReparse(string path){
  Require(Path.GetFullPath(path)==path);
  for(string node=path;node!=null;node=Path.GetDirectoryName(node)){
   Require((File.GetAttributes(node)&FileAttributes.ReparsePoint)==0);
  }
 }
 static void Acl(string path,bool directory){
  NoReparse(path);
  FileSystemSecurity acl=directory?(FileSystemSecurity)Directory.GetAccessControl(path):File.GetAccessControl(path);
  Require(acl.GetOwner(typeof(SecurityIdentifier)).Value==Owner);
  if(directory)Require(acl.AreAccessRulesProtected);
  bool appRead=false;
  foreach(FileSystemAccessRule ace in acl.GetAccessRules(true,true,typeof(SecurityIdentifier))){
   string sid=ace.IdentityReference.Value;
   Require(ace.AccessControlType==AccessControlType.Allow && (sid==Owner||sid=="S-1-5-18"||sid=="S-1-5-32-544"||sid==App));
   if(sid==App){Require(((long)ace.FileSystemRights&0xD0116)==0);appRead|=((long)ace.FileSystemRights&1)!=0;}
  }
  Require(appRead);
 }
 static bool Denied(string path,uint access){
  using(SafeFileHandle h=CreateFileW(path,access,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero)){
   int error=Marshal.GetLastWin32Error();return h.IsInvalid && error==5;
  }
 }
 static void FileCheck(FileStream stream){
  FileIdentity info;Require(GetFileInformationByHandle(stream.SafeFileHandle,out info));
  Require(info.Links==1 && (info.Attributes&0x400)==0);
 }
 // Host-only parent custody check. Unknown writable principals fail closed;
 // this adapter never repairs ACLs or grants the child parent access.
 internal static void CheckParentRule(FileSystemAccessRule ace){
  if((ace.PropagationFlags&PropagationFlags.InheritOnly)!=0)return;
  Require(ace.AccessControlType==AccessControlType.Allow);
  string sid=ace.IdentityReference.Value;
  if(sid==Owner||sid=="S-1-5-18"||sid=="S-1-5-32-544")return;
  if(((long)ace.FileSystemRights&0x500D0156L)!=0)
   throw new InvalidOperationException("HOST_CUSTODY_PARENT_WRITER:"+sid);
 }
 public static void verify_custody(){
  Require(Environment.OSVersion.Platform==PlatformID.Win32NT && Environment.Is64BitProcess);
  using(var user=WindowsIdentity.GetCurrent()){Require(user.User.Value==Owner);}
  string parent=Path.GetDirectoryName(Root);
  NoReparse(parent);
  var parentAcl=Directory.GetAccessControl(parent);
  Require(parentAcl.GetOwner(typeof(SecurityIdentifier)).Value==Owner);
  foreach(FileSystemAccessRule ace in parentAcl.GetAccessRules(true,true,typeof(SecurityIdentifier)))CheckParentRule(ace);
  Acl(Root,true);Acl(Root+@"\inputs",true);Acl(Projection,false);
  using(var stream=new FileStream(Projection,FileMode.Open,FileAccess.Read,FileShare.Read)){FileCheck(stream);}
  foreach(string path in Forbidden)Require(File.Exists(path));
 }
 static void ScorerPath(){
  // Host checks the parent hierarchy. Child checks only its allowed subtree.
  foreach(string path in new[]{Root,Root+@"\inputs",Projection})
   Require((File.GetAttributes(path)&FileAttributes.ReparsePoint)==0);
 }
 public static void verify_projection(string expectedReviewedSha256){
  Token();ScorerPath();
  Require(expectedReviewedSha256!=null && expectedReviewedSha256.Length==64);
  foreach(char c in expectedReviewedSha256)Require((c>='0'&&c<='9')||(c>='a'&&c<='f'));
  using(var stream=new FileStream(Projection,FileMode.Open,FileAccess.Read,FileShare.Read)){
   FileCheck(stream);
   using(var sha=SHA256.Create()){
    string actual=BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    Require(actual==expectedReviewedSha256);
    Require(Denied(Projection,0x40000000));
    foreach(string path in Forbidden)Require(Denied(path,0x80000000));
   }
  }
 }
}
