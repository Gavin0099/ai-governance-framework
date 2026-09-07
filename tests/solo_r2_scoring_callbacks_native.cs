// Contract cases only: no ACL mutation, real root read or AppContainer launch.
using System;
using System.Security.AccessControl;
using System.Security.Principal;
class CallbackContracts {
 static int count;
 static void Check(Action action,bool rejects){
  bool failed=false;try{action();}catch(InvalidOperationException){failed=true;}
  if(failed!=rejects)throw new Exception("CALLBACK_CONTRACT_FAILURE");count++;
 }
 static int Main(){try{return Run();}catch(Exception e){Console.WriteLine(e.GetType().Name+":"+e.Message);return 1;}}
 static int Run(){
  foreach(bool scorer in new[]{false,true}){
   var acl=SoloR2ScoringHostVerifiers.NewCustodyAcl(scorer);
   var rules=acl.GetAccessRules(true,true,typeof(SecurityIdentifier));
   if(!acl.AreAccessRulesProtected || rules.Count!=(scorer?4:3))throw new Exception("ACL_SHAPE");
   int readers=0;
   foreach(FileSystemAccessRule rule in rules){
    if(rule.AccessControlType!=AccessControlType.Allow || rule.IsInherited)throw new Exception("ACL_GRANT");
    string sid=rule.IdentityReference.Value;
    if(sid=="S-1-15-2-131220624-4122180277-3555119406-1414502418-3096179838-1091309190-3293210637"){
     readers++;
     if(rule.FileSystemRights!=(FileSystemRights.ReadAndExecute|FileSystemRights.Synchronize))throw new Exception("APP_RIGHTS");
    }else if((sid!="S-1-5-21-4017902291-1272973841-664929404-1001" && sid!="S-1-5-18" && sid!="S-1-5-32-544") || rule.FileSystemRights!=FileSystemRights.FullControl)throw new Exception("UNEXPECTED_PRINCIPAL");
   }
   if(readers!=(scorer?1:0))throw new Exception("PRIVATE_EXPOSURE");
   count++;
  }
  string hash=new string('a',64);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.Root,SoloR2ScoringHostVerifiers.Projection,hash),false);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.RealRoot,SoloR2ScoringHostVerifiers.RealProjection,hash),false);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.Root,SoloR2ScoringHostVerifiers.RealProjection,hash),true);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.RealRoot,SoloR2ScoringHostVerifiers.Projection,hash),true);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity("C:\\arbitrary",SoloR2ScoringHostVerifiers.RealProjection,hash),true);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.RealRoot,SoloR2ScoringHostVerifiers.RealProjection,null),true);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.RealRoot,SoloR2ScoringHostVerifiers.RealProjection,new string('A',64)),true);
  Check(()=>SoloR2ScoringHostVerifiers.ProjectionIdentity(SoloR2ScoringHostVerifiers.RealRoot,SoloR2ScoringHostVerifiers.RealProjection,"abc"),true);
  Check(()=>SoloR2ScoringHostVerifiers.verify_custody(SoloR2ScoringHostVerifiers.RealPrivate, SoloR2ScoringHostVerifiers.Root),true);
  Console.WriteLine("NATIVE_CALLBACK_CONTRACTS: "+count+" PASS");return 0;
 }
}
