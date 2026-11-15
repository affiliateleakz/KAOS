"""Fetch recent SEC Form 4 ownership XML for an explicitly configured issuer CIK.

Never invent trades. A separate authorized collector imports parsed disclosures.
Respect SEC fair-access limits and identify your application in User-Agent.
"""
import asyncio
import os
from urllib.parse import urlparse
import httpx
from sec_form4_parser import parse_form4

SEC_HOSTS={"www.sec.gov","sec.gov","data.sec.gov"}

async def collect_issuer_form4(cik: int, *, max_filings=15, client=None):
    if not isinstance(cik,int) or not 1<=cik<=9999999999:
        raise ValueError("Valid SEC issuer CIK required")
    if not 1<=max_filings<=25:
        raise ValueError("Maximum 25 filings per request")
    agent=os.environ.get("KAOS_SEC_USER_AGENT","")
    if "@" not in agent:
        raise RuntimeError("Set SEC User-Agent (KAOS_SEC_USER_AGENT) to an identifiable app and contact email")
    headers={"User-Agent":agent,"Accept":"application/json, application/xml, text/xml"}
    owned=client is None
    if owned: client=httpx.AsyncClient(timeout=20,headers=headers,follow_redirects=False)
    try:
        resp=await client.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json",headers=headers)
        resp.raise_for_status()
        recent=resp.json().get("filings",{}).get("recent",{})
        fields=("form","accessionNumber","primaryDocument","filingDate")
        length=min(len(recent.get(k,[])) for k in fields)
        docs=[]
        for i in range(length):
            form=recent["form"][i]
            if form not in ("4","4/A"):continue
            acc=recent["accessionNumber"][i]
            # submissions.json frequently reports values such as "xslF345X06/form4.xml".
            # That path is the browser-rendered HTML copy; the machine-readable XML is
            # served from the filing root under the same file name.
            filename=(recent["primaryDocument"][i] or "").rsplit("/",1)[-1]
            if not filename.lower().endswith(".xml") or filename.startswith(".") or ".." in filename:
                continue
            if not (acc.replace("-","").isdigit() and len(acc.replace("-",""))==18):continue
            link=f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-','')}/{filename}"
            if urlparse(link).hostname not in SEC_HOSTS:continue
            # SEC fair access allows 10 requests/second; stay well under it.
            await asyncio.sleep(0.12)
            try:
                response=await client.get(link,headers=headers)
            except httpx.HTTPError:
                continue
            response.raise_for_status()
            try: rows=parse_form4(response.text)
            except ValueError:continue
            docs.append({"filing_id":acc,"filing_date":recent["filingDate"][i],
                         "source_url":link,"form":form,"transactions":rows})
            if len(docs)>=max_filings:break
        return docs
    finally:
        if owned:await client.aclose()
