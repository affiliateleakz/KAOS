import PersonalAI from './PersonalAI';
import React, { useEffect, useState } from "react";
import { api, errMsg } from "../../lib/api";
import { StatusBadge } from "../../components/Brand";
import { Button } from "../../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { toast } from "sonner";
import { Brain, TrendingUp } from "lucide-react";

const H = ({ children }) => <h1 className="mb-6 font-heading text-2xl font-bold tracking-wide">{children}</h1>;
const Stat = ({ l, v }) => (<div className="card-surface p-4"><div className="label-mono">{l}</div><div className="mt-1 font-mono text-2xl font-bold text-[#D4AF37]">{v}</div></div>);

export function LedgerCard({ ledger }) {
  const b = ledger.balance;
  return (
    <div className="card-surface mt-6 p-0 overflow-x-auto" data-testid="affiliate-ledger">
      <div className="flex flex-wrap items-center gap-2 border-b border-[#2E2E2E] p-4">
        <TrendingUp className="h-5 w-5 text-[#D4AF37]" /><h3 className="font-heading font-semibold">3-Level Commission Ledger</h3>
        <span className="rounded bg-[#D4AF37]/15 px-2 py-0.5 font-mono text-[10px] uppercase text-[#D4AF37]" data-testid="ledger-tier">{ledger.tier} tier</span>
        <span className="font-mono text-xs text-slate-500" data-testid="ledger-note">{ledger.note}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4">
        <Stat l="In 30-day hold" v={`$${b.pending}`} /><Stat l="Available (preview)" v={`$${b.available}`} />
        <Stat l="Reversed" v={`$${b.reversed}`} /><Stat l="Paid out" v={`$${b.paid}`} />
      </div>
      <Table><TableHeader><TableRow className="border-[#2E2E2E]"><TableHead>Date</TableHead><TableHead>Level</TableHead><TableHead>Your tier</TableHead><TableHead>Rate</TableHead><TableHead>Payment</TableHead><TableHead>Amount</TableHead><TableHead>Type</TableHead></TableRow></TableHeader>
        <TableBody>
          {ledger.entries.length === 0 && <TableRow><TableCell colSpan={7} className="py-6 text-center text-slate-500">No ledger entries yet</TableCell></TableRow>}
          {ledger.entries.map((e) => (
            <TableRow key={e.entry_id} className="border-[#2E2E2E]">
              <TableCell className="font-mono text-xs text-slate-400">{e.created_at.slice(0, 10)}</TableCell>
              <TableCell className="font-mono">L{e.level}</TableCell><TableCell className="capitalize">{e.recipient_tier}</TableCell>
              <TableCell className="font-mono">{e.rate_pct}%</TableCell><TableCell className="font-mono text-slate-400">${e.base_amount}</TableCell>
              <TableCell className={`font-mono ${e.amount.startsWith("-") ? "text-red-400" : "text-[#22C55E]"}`}>${e.amount}</TableCell>
              <TableCell className="capitalize">{e.kind}</TableCell>
            </TableRow>
          ))}
        </TableBody></Table>
    </div>
  );
}

export function AIPage(){return <PersonalAI/>;}
