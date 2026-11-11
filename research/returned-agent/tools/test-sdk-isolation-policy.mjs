import test from 'node:test';import assert from 'node:assert/strict';
import {endpoint,refuseUnverifiedExperiment} from './sdk-isolation-policy.mjs';
const facts={candidate_endpoint:'ws://127.0.0.1:1235',shared_endpoint:'ws://127.0.0.1:1234',listener_identity_verified:true,process_created_by_this_run:true,separate_profile_verified:true,shared_state_writes_excluded:true,job_containment_verified:true,no_breakaway_children_verified:true,free_bytes:4e9,required_bytes:3e9,normal_load_control_completed:true};
test('explicit loopback only; no auto-discovery, credentials, routes or DNS aliases',()=>{
 for(const value of ['ws://localhost:1235','ws://127.0.0.1','wss://127.0.0.1:1235','ws://127.0.0.1:1235/path','ws://u:p@127.0.0.1:1235','ws://127.0.0.1:1235/?x=1'])assert.throws(()=>endpoint(value));
 assert.equal(endpoint(facts.candidate_endpoint),'ws://127.0.0.1:1235');
});
test('shared endpoint refused even if all claimed ownership flags are true',()=>assert.ok(refuseUnverifiedExperiment({...facts,candidate_endpoint:facts.shared_endpoint}).reasons.includes('shared_endpoint_forbidden_for_mutation')));
test('different port without owned listener remains blocked',()=>assert.ok(refuseUnverifiedExperiment({...facts,listener_identity_verified:false}).reasons.includes('owned_listener_not_proven')));
test('separate process without separate profile remains blocked',()=>assert.ok(refuseUnverifiedExperiment({...facts,separate_profile_verified:false}).reasons.includes('separate_state_not_proven')));
test('containment requires job and no breakaway proof',()=>{
 for(const key of ['job_containment_verified','no_breakaway_children_verified'])assert.ok(refuseUnverifiedExperiment({...facts,[key]:false}).reasons.includes('process_tree_containment_not_proven'));
});
test('unknown, insufficient and malformed memory budgets refused',()=>{
 for(const patch of [{free_bytes:2e9},{free_bytes:null},{required_bytes:0},{required_bytes:NaN}])assert.ok(refuseUnverifiedExperiment({...facts,...patch}).reasons.includes('memory_budget_not_met'));
});
test('abort cannot be called verified without normal-load control',()=>assert.ok(refuseUnverifiedExperiment({...facts,normal_load_control_completed:false}).reasons.includes('normal_load_control_not_completed_abort_forbidden')));
test('passing synthetic flags never becomes executable authority or live proof',()=>{
 const r=refuseUnverifiedExperiment(facts);assert.deepEqual(r.reasons,[]);assert.equal(r.model_dispatch_supported,false);assert.equal(r.model_calls,0);assert.equal(r.status,'checklist_only_requires_verified_launcher');
});
