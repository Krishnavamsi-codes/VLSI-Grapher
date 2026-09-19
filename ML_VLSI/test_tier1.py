import urllib.request, json
from collections import Counter
from sklearn.metrics import accuracy_score, f1_score
import pandas as pd

def call_api(circuit_name):
    body = json.dumps({"circuit_name": circuit_name}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8501/api/infer",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())

# ---- Test 1: 863-gate circuit ----
print("=== TEST 1: Test_add_mul_16_bit_Syn_65nm.v ===")
r = call_api("Test_add_mul_16_bit_Syn_65nm.v")
m = r["metrics"]
print("  Accuracy :", round(m["accuracy"]*100, 2), "%")
print("  F1-Micro :", round(m["f1_micro"]*100, 2), "%")
print("  F1-Macro :", round(m["f1_macro"]*100, 2), "%")
print("  Predictions count:", len(m["predictions"]))
dist = Counter(m["predictions"])
classes = ["Adder","Multiplier","Control","Subtractor","Comparator"]
for k in sorted(dist):
    print("    class", k, classes[k]+":", dist[k], "gates")
print("  Subcircuits:", len(r["subcircuits"]))

# ---- Test 2: different circuit ----
print()
print("=== TEST 2: Test_add_mul_comp_sub_16_bit_Syn_65nm.v ===")
r2 = call_api("Test_add_mul_comp_sub_16_bit_Syn_65nm.v")
m2 = r2["metrics"]
print("  Accuracy :", round(m2["accuracy"]*100, 2), "%")
print("  F1-Micro :", round(m2["f1_micro"]*100, 2), "%")
print("  F1-Macro :", round(m2["f1_macro"]*100, 2), "%")
print("  Predictions count:", len(m2["predictions"]))

# ---- Test 3: Independent recalculation from CSV ----
print()
print("=== TEST 3: Independent verification from CSV ===")
df = pd.read_csv("GNN-RE/GraphSAINT/predictions_all_nodes.csv")
for circ in ["Test_add_mul_16_bit_Syn_65nm.v", "Test_add_mul_comp_sub_16_bit_Syn_65nm.v"]:
    sub = df[df["circuit_file"] == circ].sort_values("node_id")
    y_true = sub["true_class"].values
    y_pred = sub["pred_class"].values
    csv_acc = round(accuracy_score(y_true, y_pred)*100, 2)
    csv_mic = round(f1_score(y_true, y_pred, average="micro", zero_division=0)*100, 2)
    csv_mac = round(f1_score(y_true, y_pred, average="macro", zero_division=0)*100, 2)
    print(circ)
    print("  CSV direct  acc=%s mic=%s mac=%s n=%d" % (csv_acc, csv_mic, csv_mac, len(y_true)))
