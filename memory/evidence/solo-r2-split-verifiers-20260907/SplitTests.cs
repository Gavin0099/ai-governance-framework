using System;
using System.Security.AccessControl;
using System.Security.Principal;
class SplitTests {
 static void Check(string sid, FileSystemRights rights, bool reject){
  bool failed=false;
  try {SoloR2ScoringHostVerifiers.CheckParentRule(new FileSystemAccessRule(new SecurityIdentifier(sid),rights,AccessControlType.Allow));}
  catch(InvalidOperationException){failed=true;}
  if(failed!=reject)throw new Exception("Parent ACL test failed");
 }
 static int Main(){
  Check("S-1-5-11",FileSystemRights.ReadAndExecute,false);
  Check("S-1-5-11",FileSystemRights.Modify,true);
  Check("S-1-5-11",FileSystemRights.ChangePermissions,true);
  Check("S-1-5-32-544",FileSystemRights.FullControl,false);
  Check("S-1-5-21-4017902291-1272973841-664929404-1001",FileSystemRights.Modify,false);
  Console.WriteLine("TARGETED_PARENT_RULE_TESTS: 5 PASS");
  try {SoloR2ScoringHostVerifiers.verify_custody();}
  catch(InvalidOperationException e){
   if(e.Message!="HOST_CUSTODY_PARENT_WRITER:S-1-5-11")throw;
   Console.WriteLine(e.Message);
   Console.WriteLine("CHILD_NOT_LAUNCHED; RX_NOT_GRANTED");
   return 0;
  }
  throw new Exception("Expected observed parent writer was not rejected; review current ACL before proceeding");
 }
}
