import CommunityHub,{CommunityPeople} from "./dashboard/CommunityHub";
import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, errMsg } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Brand } from "../components/Brand";
import { StrategyCard } from "../components/StrategyCard";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

export default function Profile() {
  const { username } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const profileVersion=useRef(0),currentUsername=useRef(username);currentUsername.current=username;
  const [p, setP] = useState(null);
  const [tab,setTab]=useState("posts"),[error,setError]=useState(""),[busy,setBusy]=useState(false);

  const load = () => {const version=++profileVersion.current;return api.get(`/api/profiles/${encodeURIComponent(username)}`).then(r=>{if(version===profileVersion.current){setP(r.data);setError("");}}).catch(e=>{if(version===profileVersion.current)setError(errMsg(e));});};
  useEffect(() => {setP(null);setError("");setTab("posts");load();return()=>{profileVersion.current++;};}, [username]);

  const toggleFollow = async () => {
    if (!user) return nav("/login");
    setBusy(true);try {
      p.isFollowing ? await api.delete(`/api/users/${encodeURIComponent(username)}/follow`) : await api.post(`/api/users/${encodeURIComponent(username)}/follow`);
      if(currentUsername.current===username)await load();
    } catch(e) { toast.error(errMsg(e)); } finally {setBusy(false);}
  };

  if(error)return <div className="p-8 text-amber-200" role="alert">{error} <button onClick={load}>Retry profile</button></div>;
  if (!p) return <div className="flex min-h-screen items-center justify-center bg-[#080808] text-slate-400">Loading profile…</div>;

  return (
    <div className="min-h-screen bg-[#080808] text-white">
      <div className="glass-nav sticky top-0 z-40 flex items-center justify-between px-6 py-4">
        <Brand /><Link to="/dashboard" className="text-sm text-slate-300 hover:text-white">Dashboard</Link>
      </div>
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="card-surface flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#1A1A1A] font-heading text-2xl font-bold text-[#D4AF37]">
            {(p.displayName || p.username || "?")[0].toUpperCase()}
          </div>
          <div className="flex-1">
            <h1 className="font-heading text-2xl font-bold">{p.displayName}</h1>
            <p className="font-mono text-sm text-[#D4AF37]">@{p.username}</p>
            <p className="mt-1 text-sm text-slate-400">{p.bio || "No bio yet."}</p>
          </div>
          {user && user.username !== username && (
            <Button data-testid="profile-follow-button" disabled={busy} onClick={toggleFollow} className={p.isFollowing ? "bg-[#1A1A1A] text-white border border-[#3A3A3A]" : "bg-[#d4af37] text-black font-semibold"}>
              {p.isFollowing ? "Following" : "Follow"}
            </Button>
          )}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-4">
          {[["Public Strategies", p.publicStrategies], ["Followers", p.followers], ["Following", p.following]].map(([l, v]) => (
            <div key={l} className="card-surface p-4 text-center">
              <div className="font-mono text-2xl font-bold text-[#D4AF37]">{v}</div>
              <div className="label-mono mt-1">{l}</div>
            </div>
          ))}
        </div>
        <nav aria-label="Member profile sections" className="my-6 flex flex-wrap gap-2">{["posts","strategies","followers","following"].map(value=><button key={value} onClick={()=>setTab(value)} aria-current={tab===value?"page":undefined} className={"rounded border border-[#70582d] px-4 py-2 capitalize "+(tab===value?"bg-[#d4af37] text-black":"text-[#e8c46f]")}>{value}</button>)}</nav>
        {tab==="posts"&&<CommunityHub key={username} author={username} embedded/>}
        {tab==="strategies"&&<div className="grid gap-6 md:grid-cols-2">{(p.strategies||[]).map(s=><StrategyCard key={s.id} s={s} onChange={load}/>)}</div>}
        {["followers","following"].includes(tab)&&(user?<CommunityPeople username={username} connection={tab} onFollow={load}/>:<Link to="/login">Sign in to see this trading circle</Link>)}

      </div>
    </div>
  );
}
