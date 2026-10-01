#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

CASES=[
 ("reject","Bath & Body Works","Cherry Blossom","Bath & Body Works Japanese Cherry Blossom / Parfüm"),
 ("reject","Victoria's Secret","Bombshell Eau de Parfum","Victoria's Secret Bombshell Bronze Eau de Parfum"),
 ("reject","Victoria's Secret","Tease Eau de Parfum","Victoria's Secret Tease Sugar Fleur Seyahat Boyu Eau De Parfum"),
 ("reject","Victoria's Secret","Very Sexy","Victoria's Secret Very Sexy Scarlet Eau de Parfum"),
 ("reject","Victoria's Secret","Very Sexy Eau de Parfum","Victoria's Secret Very Sexy Euphoric Eau de Parfum 50 ml"),
 ("reject","Oriflame","Giordani Gold Essenza (Parfum)","Oriflame Giordani Gold Essenza Supreme Vücut ve Saç Parfüm Misti"),
 ("reject","Oriflame","Eclat Femme","Oriflame Eclat Femme Weekend EdT"),
 ("reject","Oriflame","Amber Elixir","Oriflame Amber Elixir Mystery EdP"),
 ("accept","Victoria's Secret","Bombshell Eau de Parfum","Victoria's Secret Bombshell Eau de Parfum"),
 ("accept","Victoria's Secret","Very Sexy Night","Victoria's Secret Very Sexy Night Eau de Parfum"),
 ("accept","Oriflame","Amber Elixir Mystery","Oriflame Amber Elixir Mystery EdP"),
 ("accept","Oriflame","Eclat Homme","Oriflame Eclat Homme EdT"),
 ("accept","Calvin Klein","Euphoria (Eau de Parfum)","Calvin Klein Euphoria EDP 100 ml Kadın Parfüm"),
 ("reject","Calvin Klein","Deep Euphoria (Eau de Parfum)","Calvin Klein Euphoria EDP 100 ml Kadın Parfüm"),
 ("accept","Dior","Sauvage Eau de Parfum","Dior Sauvage Eau de Parfum refillable Eau de Parfum - citrus and vanilla notes"),
 ("accept","Tom Ford","Oud Wood","Tom Ford Oud Wood EDP 50 ml Parfüm"),
 ("accept","Versace","Eros (Eau de Parfum)","Versace Eros EDP 50 ml Erkek Parfüm"),
 ("reject","Versace","Eros (Eau de Parfum)","Versace Eros Pour Femme EDP 100 ml Kadın Parfüm"),
]

bad=[]
for expected,brand,product,candidate in CASES:
    got=core.variant_compatible(brand,product,candidate)
    want=(expected=="accept")
    print(("PASS" if got==want else "FAIL"),expected,brand,"|",product,"|",candidate,"=>",got)
    if got!=want: bad.append((expected,brand,product,candidate,got))

if bad:
    print("REGRESSION_FAILURES",len(bad))
    raise SystemExit(1)
print("REGRESSION_OK",len(CASES))
