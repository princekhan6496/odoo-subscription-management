const API_URL=process.env.NEXT_PUBLIC_API_URL??"http://localhost:8000";
function csrfToken(){
 if(typeof document==="undefined") return "";
 const prefix=`${process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME??"brightloop_csrf"}=`;
 const item=document.cookie.split(";").map(v=>v.trim()).find(v=>v.startsWith(prefix));
 return item?decodeURIComponent(item.slice(prefix.length)):"";
}
export async function api<T>(path:string,options:RequestInit={},_legacyToken?:string):Promise<T>{
 const headers=new Headers(options.headers);
 if(options.body&&!(options.body instanceof FormData))headers.set("Content-Type","application/json");
 const method=(options.method??"GET").toUpperCase();
 if(!["GET","HEAD","OPTIONS"].includes(method)){
  const csrf=csrfToken(); if(csrf) headers.set("X-CSRF-Token",csrf);
 }
 const r=await fetch(`${API_URL}/api/v1${path}`,{...options,headers,credentials:"include",cache:"no-store"});
 if(!r.ok){let message=`Request failed (${r.status})`;try{const e=await r.json();if(typeof e.detail==="string")message=e.detail}catch{}throw new Error(message)}
 if(r.status===204)return undefined as T;if(r.headers.get("content-type")?.includes("application/pdf"))return await r.blob() as T;return r.json() as Promise<T>;
}
export {API_URL};
