"""Post-selection exploratory parameter interventions, all outcomes unchanged."""
from copy import deepcopy
from .evidence import discover
from deviation.markets.contracts import Rejection


def sensitivity(bundle):
    rows=[]
    grid={"external":[0,1,2,3,6,12],"capital":[0,1,2,3,8],
          "fee":[0,1,2,3],"liquidity":[1,3,20],"action_limit":[0,1,100]}
    controller=bundle["controller"]
    for dimension,values in grid.items():
        for value in values:
            s=deepcopy(bundle["scenario"])
            if dimension=="external":
                for weights in s["controllers"][controller]["external_weights"].values():
                    for m in weights:weights[m]=value
            elif dimension=="capital":
                members=sorted(a for a,v in s["agents"].items() if v["controller"]==controller)
                for i,a in enumerate(members):s["agents"][a]["wallet"]=value//len(members)+int(i<value%len(members))
                s["controllers"][controller]["cash_cap"]=value
            elif dimension=="fee":s["economics"]["fee"]=value
            elif dimension=="liquidity":s["economics"]["b"]=value
            else:s["economics"]["action_limit"]=value
            row={"intervention":dimension,"value":value,"label":"POST_SELECTION_EXPLORATORY_NOT_REPLICATION"}
            try:
                b=discover(s,controller,bundle["mechanism"],**bundle["options"])
                e=b["evidence"]
                row.update(status="EVALUATED",classification=e["classification"],gain=e["gain_vs_signal_following"],
                    expected_welfare_loss=e["environment_expected_welfare_loss"],
                    method=e["search"]["method"],input_sha256=e["input_sha256"],
                    all_selected_nonnoop_commands_accepted=e["all_selected_nonnoop_commands_accepted"])
            except Rejection as x:row.update(status="NOT_EVALUATED",reason=str(x))
            rows.append(row)
    return {"version":"attack-sensitivity-1","basis_case":bundle["evidence"]["sha256"],"cases":rows}
