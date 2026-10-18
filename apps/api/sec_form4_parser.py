"""Parse SEC ownership Form 4 XML into disclosed transaction rows.

Parsing only: does not download filings or assert that supplied XML is authentic.
The authorized collector must fetch and preserve the official SEC source URL.
"""
from datetime import date
from xml.etree import ElementTree as ET

def parse_form4(xml_data: str):
    if len(xml_data)>2_000_000 or "<!DOCTYPE" in xml_data.upper() or "<!ENTITY" in xml_data.upper():
        raise ValueError("Unsafe or oversized SEC XML")
    try:
        root=ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError("Malformed Form 4 XML") from exc
    def find(node,path):
        found=node.find(path)
        return (found.text or "").strip() if found is not None else ""
    if root.tag.split("}")[-1]!="ownershipDocument":
        raise ValueError("Not an ownership document")
    issuer=find(root,".//issuerTradingSymbol")
    owner=find(root,".//reportingOwner/reportingOwnerId/rptOwnerName")
    if not issuer or not owner:
        raise ValueError("Missing SEC issuer or reporting owner")
    rows=[]
    for transaction in root.findall(".//nonDerivativeTransaction"):
        code=find(transaction,"./transactionCoding/transactionCode").upper()
        side=find(transaction,"./transactionAmounts/transactionAcquiredDisposedCode/value").upper()
        action={"P":"buy","S":"sell"}.get(code)
        if not action:
            action="grant" if code in ("A","G") else "exercise" if code in ("M","C") else "other"
        if code=="P" and side=="D" or code=="S" and side=="A":
            action="other"
        txdate=find(transaction,"./transactionDate/value")
        if not txdate:
            continue
        try: date.fromisoformat(txdate)
        except ValueError: raise ValueError("Invalid Form 4 transaction date") from None
        rows.append({"filer":owner,"ticker":issuer,"asset":find(root,".//issuerName") or issuer,
            "action":action,"transaction_date":txdate,
            "shares":find(transaction,"./transactionAmounts/transactionShares/value"),
            "price_per_share":find(transaction,"./transactionAmounts/transactionPricePerShare/value"),
            "derivative":False})
    return rows
