"""On-demand SEC 13F information-table discovery from official EDGAR indexes."""
import os
import httpx
from sec_13f_parser import parse_13f_information_table

async def fetch_13f_holdings(cik: int, *, max_filings=5, client=None):
    if type(cik) is not int or not 1 <= cik <= 9999999999:
        raise ValueError("Valid SEC CIK required")
    if not 1 <= max_filings <= 10:
        raise ValueError("Maximum 10 filings")
    agent=os.getenv("KAOS_SEC_USER_AGENT","")
    if "@" not in agent:
        raise RuntimeError("SEC User-Agent contact is required")
    headers={"User-Agent":agent,"Accept":"application/json, text/xml, application/xml"}
    owns=client is None
    if owns: client=httpx.AsyncClient(timeout=20,follow_redirects=False)
    try:
        url=f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        response=await client.get(url,headers=headers)
        response.raise_for_status()
        recent=response.json().get("filings",{}).get("recent",{})
        keys=("form","accessionNumber","filingDate")
        size=min(len(recent.get(k,[])) for k in keys)
        output=[]
        for i in range(size):
            if recent["form"][i] not in ("13F-HR","13F-HR/A"):continue
            accession=recent["accessionNumber"][i]
            number=accession.replace("-","")
            if not (len(number)==18 and number.isdigit()):continue
            base=f"https://www.sec.gov/Archives/edgar/data/{cik}/{number}"
            listing=await client.get(base+"/index.json",headers=headers)
            listing.raise_for_status()
            files=listing.json().get("directory",{}).get("item",[])
            rows=None; source=None
            for entry in files:
                name=entry.get("name","")
                if not name.lower().endswith(".xml") or "/" in name or ".." in name:continue
                xml=await client.get(base+"/"+name,headers=headers)
                xml.raise_for_status()
                try: parsed=parse_13f_information_table(xml.text)
                except ValueError:continue
                if parsed:
                    rows=parsed;source=base+"/"+name;break
            if rows is not None:
                output.append({"filing_id":accession,"filing_date":recent["filingDate"][i],
                  "source_url":source,"form":recent["form"][i],"holdings":rows})
            if len(output)>=max_filings:break
        return output
    finally:
        if owns:await client.aclose()
