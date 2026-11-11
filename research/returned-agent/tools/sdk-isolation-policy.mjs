// Evidence gate only. It never starts a process or dispatches a model request.
export function endpoint(value){
 const u=new URL(value);
 if(u.protocol!=='ws:'||u.hostname!=='127.0.0.1'||!u.port||u.username||u.password||u.pathname!=='/'||u.search||u.hash)throw Error('Explicit loopback WebSocket root required');
 return u.origin;
}
export function isolationBlockers(e){
 const errors=[];
 let same=true;try{same=endpoint(e.candidate_endpoint)===endpoint(e.shared_endpoint);}catch{errors.push('invalid_or_missing_explicit_endpoint');}
 if(same)errors.push('shared_endpoint_forbidden_for_mutation');
 if(!e.listener_identity_verified||!e.process_created_by_this_run)errors.push('owned_listener_not_proven');
 if(!e.separate_profile_verified||!e.shared_state_writes_excluded)errors.push('separate_state_not_proven');
 if(!e.job_containment_verified||!e.no_breakaway_children_verified)errors.push('process_tree_containment_not_proven');
 if(!Number.isSafeInteger(e.free_bytes)||!Number.isSafeInteger(e.required_bytes)||e.required_bytes<=0||e.free_bytes<e.required_bytes)errors.push('memory_budget_not_met');
 if(!e.normal_load_control_completed)errors.push('normal_load_control_not_completed_abort_forbidden');
 return errors;
}
export function refuseUnverifiedExperiment(e){
 const reasons=isolationBlockers(e);
 // An evidence object is not authentication. Passing this checklist is never a launch capability.
 return {status:reasons.length?'blocked_before_model_dispatch':'checklist_only_requires_verified_launcher',reasons,model_dispatch_supported:false,model_calls:0};
}
