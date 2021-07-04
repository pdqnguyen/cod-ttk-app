**Put measurements in a Google spreadsheet**

![spreadsheet](/assets/images/example/spreadsheet.png)

[Click here](https://docs.google.com/spreadsheets/d/155GmFod_Kuo5khmGhNlIjKf53x9Tlw6sey4p3VZxpjE/edit?usp=sharing)
for an example spreadsheet you can make a copy of.
The first tab has screen/FOV measurements for determining angular resolution.
The second tab is a template with the equations already entered in for converting from
screen measurements to degrees.
The rest of the tabs are my own past measurements as examples.

**Input x and y values in degrees**

![inputs](/assets/images/example/inputs.png)

Round off to the nearest 0.05 degrees. This isn't meant to be super accurate anyway.

**Example results**

The first graph shows chest TTK up to 100 meters, with zero-recoil curves shown
in dashed lines for comparison.
See the corresponding [TrueGameData page](https://www.truegamedata.com/?share=bTECUV)
for the full loadout specs.
Adjusting for recoil results in a much greater TTK for many of these weapons,
exceeding one second beyond ranges of about 60 meters.
The C58, which is the strongest of these weapons based on damage alone, has a slower
TTK than the much more accurate FARA beyond about 40 meters due to its recoil, but
it still outpaces the XM4 at all ranges.
The Krig 6 is often lauded for its incredibly low recoil, but given its very low
damage output it still cannot compete with the C58 and FARA, and it only slightly
beats the XM4 at 30-55 meters.

![TTK](/assets/images/example/chest/ttk_no_ads_no_recoil.png)

Below are DPS graphs for headshots (with zero-recoil curves shown as well) and
chest shots. These show that it may be (at least based on my recoil measurements)
impractical aiming for headshots beyond about 30 meters. Even for the laser-accurate
FARA, headshot DPS drops below chest DPS at 30 meters. This really emphasizes how
important chest multipliers can be (often being far more important that head damage
multipliers, as was the case with the CR-56 AMAX before its multiple nerfs).

![DPS_head](/assets/images/example/head/dps.png)
![DPS_chest](/assets/images/example/chest/dps.png)


### Future work
Here are some things that *may* be implemented in the future.
- [ ]  Segment plot: horizontal bar showing dominant weapon at each distance bin.
- [ ]  Better hitbox geometry, or average over various hitboxes representing different encounter angles.
- [ ]  Add a slider for enemy HP.
- [ ]  Add option of including/excluding reload time.
- [ ]  Show percentage of shots hitting each hitbox region (e.g. 10% head, 25% chest, etc.).
