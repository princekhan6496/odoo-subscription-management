"use client";
import {FormEvent,useEffect,useState} from "react";
import {api} from "@/lib/api";

export default function ResetPasswordPage(){
 const [token,setToken]=useState("");useEffect(()=>{setToken(new URLSearchParams(window.location.search).get("token")??"")},[]);
 const [password,setPassword]=useState("");const [message,setMessage]=useState("");const [error,setError]=useState(false);const [busy,setBusy]=useState(false);
 const submit=async(e:FormEvent)=>{e.preventDefault();setBusy(true);setMessage("");try{const result=await api<{message:string}>("/auth/reset-password",{method:"POST",body:JSON.stringify({token,new_password:password})});setMessage(result.message)}catch(err){setError(true);setMessage(err instanceof Error?err.message:"Unable to reset password")}finally{setBusy(false)}};
 return <main className="flex min-h-screen items-center justify-center px-5"><form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-7 shadow-sm"><p className="text-xs font-bold uppercase tracking-widest text-slate-400">Brightloop security</p><h1 className="mt-2 text-2xl font-bold">Choose a new password</h1><p className="mt-2 text-sm text-slate-500">Use at least 9 characters, including uppercase, lowercase and a special character.</p><label className="mt-7 block text-sm font-semibold">New password<input required minLength={9} type="password" value={password} onChange={e=>setPassword(e.target.value)} className="mt-2 w-full rounded-lg border border-slate-200 p-3 font-normal"/></label><button disabled={!token||busy} className="mt-6 w-full rounded-lg bg-[#17212b] p-3 text-sm font-semibold text-white disabled:opacity-50">{busy?"Updating…":"Update password"}</button>{!token&&<p className="mt-4 text-sm text-rose-600">This reset link is missing its token.</p>}{message&&<p role="status" className={`mt-4 text-sm ${error?"text-rose-600":"text-emerald-700"}`}>{message}</p>}</form></main>;
}
