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

**Example plots**

The first graph shows chest TTK up to 100 meters, with zero-recoil curves shown
in dashed lines for comparison.
See the corresponding [TrueGameData page](https://www.truegamedata.com/?share=EDHovz)
for the full loadout specs.
Adjusting for recoil results in a much greater simulated TTK for many of these weapons
relative to their theoretical TTK.
The FARA, despite having the lowest long-range TTK on paper, does noticeably worse
than the weaker Krig 6 due to its higher recoil.

![TTK](/assets/images/example/chest/ttk_nr.png)

Below are headshot TTKs (with zero-recoil curves shown as well).
These show that, at least based on my recoil measurements,
headshots can give a huge advantage to certain weapons with high headshot
multipliers like the M13 if a player is close enough to take advantage of them.
However, the practicality of aiming for headshots plummets quickly with distance.
The M13 can manage a better headshot TTK than its chest TTK up to about 40 meters,
whereas on the other extreme, weapons with very high recoil and/or low headshot
multipliers such as the FARA are virtually incapable of benefiting from headshots
except at close ranges, at which point SMGs would triumph anyway.

![TTK_head](/assets/images/example/head/ttk_nr.png)

Below, ADS times are added to the chest damage TTKs, showing that ADS speed can still
contribute significantly even at ranges where TTK is dominated by recoil effects.

![TTK_ads](/assets/images/example/chest/ttk_ads.png)


### Future work
Here are some things that *may* be implemented in the future.
- [ ]  Segment plot: horizontal bar showing dominant weapon at each distance bin.
- [ ]  Better hitbox geometry, or average over various hitboxes representing different encounter angles.
- [ ]  Add a slider for enemy HP.
- [ ]  Add option of including/excluding reload time.
- [ ]  Show percentage of shots hitting each hitbox region (e.g. 10% head, 25% chest, etc.).
